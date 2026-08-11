use super::super::dev::*;
use super::content::{norm_seg, Proxies};
use super::tree::{NodeType, SortMode};
use crate::tui::theme::Theme;
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, List, ListItem};

pub fn render(content: &Proxies, f: &mut Frame, area: Rect, state: &mut ListState) {
    let theme = Theme::get();
    let section = theme.section("proxies");

    // Clamp cursor to valid range
    if let Some(idx) = state.selected() {
        let len = content.tree.len();
        if len == 0 {
            state.select(None);
        } else if idx >= len {
            state.select(Some(len.saturating_sub(1)));
        }
    } else if !content.tree.is_empty() {
        state.select(Some(0));
    }

    let block = Block::bordered()
        .border_style(section.border)
        .title(Proxies::TITLE);

    let spinner_str = content.testing_since.map(|since| {
        let elapsed = since.elapsed().as_millis() as usize;
        let spinner = ['|', '/', '-', '\\'];
        let c = spinner[(elapsed / 100) % 4];
        let msg = content.error.as_deref().unwrap_or("Testing...");
        format!(" {c} {msg}")
    });

    if content.tree.is_empty() {
        let msg = spinner_str
            .as_deref()
            .unwrap_or(content.error.as_deref().unwrap_or(""));
        let widget = ratatui::widgets::Paragraph::new(msg).block(block);
        f.render_widget(widget, area);
        return;
    }

    // Compute filtered view
    let all_nodes = &content.tree.nodes;
    let filter_pat = content.filter.as_deref().map(|p| p.to_lowercase());
    let filter_active = filter_pat.is_some();
    // filter 为 None 时跳过 collect，直接用身份区间
    let filtered_indices: Vec<usize> = match filter_pat.as_deref() {
        Some(pat) => all_nodes
            .iter()
            .enumerate()
            .filter(|(_, node)| node.lower_name.contains(pat))
            .map(|(i, _)| i)
            .collect(),
        None => Vec::new(),
    };
    let view_len = if filter_active {
        filtered_indices.len()
    } else {
        all_nodes.len()
    };
    // 视图位置 -> 树索引（filter 未启用时即身份映射）
    let view_index = |vi: usize| -> usize {
        if filter_active {
            filtered_indices[vi]
        } else {
            vi
        }
    };

    let current = state.selected().unwrap_or(0);
    let filter_cursor = cursor_in_view(current, all_nodes.len(), &filtered_indices, filter_active);

    // Build footer
    let mut footer_parts: Vec<String> = Vec::new();

    // Sort indicator
    if current < all_nodes.len() {
        let node = &all_nodes[current];
        let group_resolved: Option<&str> = match node.node_type {
            NodeType::Folder => Some(node.name.as_str()),
            NodeType::Link | NodeType::File => node.parent.as_deref(),
        };
        if let Some(gname) = group_resolved
            && let Some(idx) = content.tree.find_folder_index(gname)
        {
            match content.tree.nodes[idx].sort_mode {
                SortMode::ByDelay => footer_parts.push("delay ".to_owned()),
                SortMode::ByName => footer_parts.push("name ".to_owned()),
                SortMode::None => {}
            }
        }
    }

    // Filter indicator
    if let Some(ref f) = content.filter {
        footer_parts.push(format!("/ {f} "));
    }

    // Hide-dead indicator
    if content.tree.hide_dead {
        footer_parts.push(format!("hide dead: on ({} hidden) ", content.dead_count));
    }

    let footer = footer_parts.join("");

    let block = if let Some(ref s) = spinner_str {
        block.title_bottom(Line::raw(s.as_str()))
    } else if !footer.is_empty() {
        block.title_bottom(Line::raw(footer).right_aligned().reversed())
    } else {
        block
    };

    let sel_abs = filter_cursor.unwrap_or(0);
    let visible = area.height.saturating_sub(2) as usize;
    let (start, end) = view_window(sel_abs, view_len, visible);

    // 节点名段对齐（宽度由 content.seg_widths 缓存提供，树重建时更新）
    let aligned_name = |node: &super::tree::NodeItem| -> String {
        let mut out = String::new();
        let mut i = 0;
        for seg in node.name.split('-') {
            if norm_seg(seg).eq_ignore_ascii_case(&node.proxy_type) {
                continue;
            }
            if i > 0 {
                out.push('-');
            }
            out.push_str(seg);
            let w = content
                .seg_widths
                .get(i)
                .copied()
                .unwrap_or(unicode_width::UnicodeWidthStr::width(seg));
            out.push_str(&" ".repeat(w.saturating_sub(unicode_width::UnicodeWidthStr::width(
                seg,
            ))));
            i += 1;
        }
        out
    };

    let items: Vec<ListItem> = (start..end)
        .map(|vi| {
            let node = &all_nodes[view_index(vi)];
            let indent = "  ".repeat(node.depth);
            let display_name = if node.node_type == NodeType::File {
                aligned_name(node)
            } else {
                node.name.clone()
            };
            let prefix = match node.node_type {
                NodeType::Folder => {
                    if node.expanded {
                        "▼"
                    } else {
                        "▶"
                    }
                }
                NodeType::Link => {
                    if node.is_now {
                        "*"
                    } else {
                        " "
                    }
                }
                NodeType::File => {
                    if node.is_now {
                        "*"
                    } else {
                        " "
                    }
                }
            };
            let style = match node.node_type {
                NodeType::Folder => section.border,
                NodeType::Link => section
                    .extra
                    .get("node_link")
                    .copied()
                    .unwrap_or(section.text),
                _ => section
                    .extra
                    .get("node_file")
                    .copied()
                    .unwrap_or(section.text),
            };

            let mut spans = vec![Span::styled(
                format!("{indent} {prefix} {display_name}  "),
                style,
            )];

            if !node.proxy_type.is_empty() {
                spans.push(Span::styled(format!("[{}]", node.proxy_type), style));
            }

            if node.node_type != NodeType::Folder {
                if node.tcp {
                    spans.push(Span::styled(
                        " TCP",
                        section
                            .extra
                            .get("node_tcp")
                            .copied()
                            .unwrap_or(section.text),
                    ));
                }
                if node.udp {
                    spans.push(Span::styled(
                        " UDP",
                        section
                            .extra
                            .get("node_udp")
                            .copied()
                            .unwrap_or(section.text),
                    ));
                }
            }

            if let Some(d) = node.delay {
                let delay_str = if d == 0 {
                    "  FAIL".to_owned()
                } else {
                    format!("  {}ms", d)
                };
                spans.push(Span::styled(delay_str, style));
            }

            ListItem::new(Line::from(spans))
        })
        .collect();

    if view_len == 0 {
        state.select(None);
    }

    let list = List::new(items)
        .block(block)
        .highlight_style(section.highlight);

    // 渲染用临时 ListState：state.selected 始终保持树索引，窗口内偏移只存在于临时状态
    let mut list_state = ListState::default().with_selected(Some(sel_abs - start));
    f.render_stateful_widget(list, area, &mut list_state);
}

/// 视图内光标位置：过滤时取 filtered 中的匹配位置（精确命中 > 首个 >= current > 最后一个），
/// 否则为身份视图下的树索引。越界返回 None。
fn cursor_in_view(
    current: usize,
    all_len: usize,
    filtered: &[usize],
    filter_active: bool,
) -> Option<usize> {
    if filter_active {
        if filtered.is_empty() {
            (current < all_len).then_some(current)
        } else {
            let mut exact = None;
            let mut first_ge = None;
            for (pos, &i) in filtered.iter().enumerate() {
                if exact.is_none() && i == current {
                    exact = Some(pos);
                }
                if first_ge.is_none() && i >= current {
                    first_ge = Some(pos);
                }
                if exact.is_some() {
                    break;
                }
            }
            exact.or(first_ge).or(Some(filtered.len() - 1))
        }
    } else if current < all_len {
        Some(current)
    } else {
        None
    }
}

/// 渲染窗口 [start, end)（视图索引区间），selected 恒在窗口内。
fn view_window(sel: usize, view_len: usize, visible: usize) -> (usize, usize) {
    let start = sel.saturating_sub(visible);
    let end = (sel + visible + 1).min(view_len).max(start);
    (start, end)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cursor_identity_without_filter() {
        assert_eq!(cursor_in_view(7, 21, &[], false), Some(7));
        assert_eq!(cursor_in_view(20, 21, &[], false), Some(20));
        assert_eq!(cursor_in_view(21, 21, &[], false), None);
    }

    #[test]
    fn cursor_snaps_to_nearest_match_with_filter() {
        let filtered = vec![2, 5, 8];
        assert_eq!(cursor_in_view(5, 21, &filtered, true), Some(1));
        assert_eq!(cursor_in_view(3, 21, &filtered, true), Some(1));
        assert_eq!(cursor_in_view(0, 21, &filtered, true), Some(0));
        assert_eq!(cursor_in_view(9, 21, &filtered, true), Some(2));
    }

    #[test]
    fn cursor_empty_filter_keeps_tree_position() {
        assert_eq!(cursor_in_view(3, 21, &[], true), Some(3));
        assert_eq!(cursor_in_view(21, 21, &[], true), None);
    }

    #[test]
    fn window_keeps_selected_visible() {
        assert_eq!(view_window(2, 21, 5), (0, 8));
        assert_eq!(view_window(0, 21, 5), (0, 6));
        assert_eq!(view_window(0, 0, 5), (0, 0));
        let (start, end) = view_window(20, 21, 5);
        assert!(start <= 20 && 20 < end);
        assert_eq!(20 - start, 5);
    }

    #[test]
    fn scroll_does_not_drift_selection() {
        // H3 回归：21 节点、每屏 5 行，一路滚到底，光标必须始终等于树索引且在窗口内
        let mut selected = 0usize;
        for _ in 0..20 {
            selected += 1;
            let cur = cursor_in_view(selected, 21, &[], false).unwrap();
            let (start, end) = view_window(cur, 21, 5);
            assert_eq!(cur, selected, "selected 必须保持为树索引");
            assert!(start <= selected && selected < end, "selected 必须在窗口内");
        }
        assert_eq!(selected, 20);
    }
}
