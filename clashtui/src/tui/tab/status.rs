use ratatui::{text::Text, widgets::Paragraph};

use super::dev::*;

newtype_tab!(StatusTab(Tab<Status>));

#[derive(Clone, Copy)]
enum Key {}

impl TryFrom<&crate::tui::Key> for Key {
    type Error = ();

    fn try_from(_: &crate::tui::Key) -> Result<Self, Self::Error> {
        Err(())
    }
}

use crate::functions::restful::{self, config_struct::*};

macro_rules! tri {
    ($e:expr) => {
        match $e {
            Ok(v) => v,
            Err(e) => {
                crate::tui::widget::popmsg::Confirm::err(e);
                return do_nothing();
            }
        }
    };
    ($e:expr, or_cancel) => {
        match $e {
            Ok(v) => v,
            Err(_) => return do_nothing(),
        }
    };
    ($e:expr, or_set) => {
        match $e {
            Ok(v) => v,
            Err(e) => {
                return wrapper(move |content: &mut Self| {
                    content.error = Some(e.to_string());
                });
            }
        }
    };
}

#[derive(Default)]
struct Status {
    config: Option<ClashConfig>,
    version: Option<String>,
    error: Option<String>,
    paused: bool,
}

impl BasicTabContent for Status {
    type Key = Key;

    type State = ();

    const TITLE: &str = "Status";

    fn after_sync(&self, task_set: &mut FutureSet<Self>) {
        if self.paused {
            return;
        }
        async {
            tokio::time::sleep(std::time::Duration::from_secs(1)).await;

            let version = tri!(
                tokio::task::spawn_blocking(restful::control::version)
                    .await
                    .unwrap(),
                or_set
            );
            let config = tri!(
                tokio::task::spawn_blocking(restful::config::fetch)
                    .await
                    .unwrap(),
                or_set
            );

            wrapper(move |content: &mut Self| {
                content.version = Some(version);
                content.config = Some(config);
            })
        }
        .spawn_at(task_set);
    }

    fn on_enter(&mut self, task_set: &mut FutureSet<Self>, _state: &mut Self::State) {
        self.paused = false;

        if self.version.is_none() {
            self.error = Some("Detecting...".to_owned());
        }

        async {
            let version = tri!(
                tokio::task::spawn_blocking(restful::control::version)
                    .await
                    .unwrap(),
                or_set
            );
            let config = tri!(
                tokio::task::spawn_blocking(restful::config::fetch)
                    .await
                    .unwrap(),
                or_set
            );

            wrapper(move |content: &mut Self| {
                content.version = Some(version);
                content.config = Some(config);
                content.error = None;
            })
        }
        .spawn_at(task_set);
    }

    fn on_leave(&mut self, _task_set: &mut FutureSet<Self>, _state: &mut Self::State) {
        self.paused = true;
    }
}

impl TabContent for Status {
    fn init(&mut self, _task_set: &mut FutureSet<Self>, _state: &mut Self::State) {
        self.paused = true;
        self.error = Some("Waiting".to_owned());
    }

    fn handle_key_event(
        &mut self,
        _key: Self::Key,
        _task_set: &mut FutureSet<Self>,
        _state: &mut Self::State,
    ) {
    }

    fn render(&self, f: &mut Frame, area: Rect, _state: &mut Self::State) {
        let block = Block::bordered()
            .border_style(Theme::get().section("status").border)
            .title(Self::TITLE);
        let mut lines: Vec<String> = vec![];
        if let Some(e) = self.error.as_deref() {
            lines.push(format!("error: {e}"));
        }
        if let Some(ref ver) = self.version {
            lines.push(format!("version: {ver}"));
        }
        if let Some(cfg) = self.config.as_ref() {
            lines.extend(cfg.build());
        }
        lines.push(crate::tui::monitor::status_line());
        if lines.is_empty() {
            lines.push("Waiting".to_owned());
        }
        let widget = Paragraph::new(Text::from_iter(lines)).block(block);
        f.render_widget(widget, area);
    }
}
