use crate::functions::restful::proxies;
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

pub static ENABLED: AtomicBool = AtomicBool::new(true);
static STATUS: Mutex<Option<String>> = Mutex::new(None);

const GROUP: &str = "ai";
const THRESHOLD_MS: u64 = 1200;
const CHECK_INTERVAL: Duration = Duration::from_secs(30);
const DELAY_TIMEOUT: u64 = 5000;

pub fn toggle() -> bool {
    let v = !ENABLED.load(Ordering::Relaxed);
    ENABLED.store(v, Ordering::Relaxed);
    if v {
        *STATUS.lock().unwrap() = None;
    }
    v
}

pub fn status_line() -> String {
    let on = ENABLED.load(Ordering::Relaxed);
    let st = STATUS.lock().unwrap().clone();
    match st {
        Some(s) if on => format!("monitor: on | {s}"),
        _ if on => "monitor: on | waiting for first check".to_owned(),
        _ => "monitor: off".to_owned(),
    }
}

fn set_status(s: String) {
    *STATUS.lock().unwrap() = Some(s);
}

pub async fn run() {
    loop {
        if ENABLED.load(Ordering::Relaxed) {
            check_once().await;
        }
        tokio::time::sleep(CHECK_INTERVAL).await;
    }
}

async fn check_once() {
    let res = match tokio::task::spawn_blocking(proxies::fetch_proxies).await {
        Ok(Ok(r)) => r,
        _ => {
            set_status("api unreachable".to_owned());
            return;
        }
    };
    let Some(info) = res.proxies.get(GROUP) else {
        set_status(format!("{GROUP}: group not found"));
        return;
    };
    let Some(now) = info.now.clone() else {
        set_status(format!("{GROUP}: no current node"));
        return;
    };
    let Some(all) = info.all.clone() else {
        set_status(format!("{GROUP}: no node list"));
        return;
    };

    let now_clone = now.clone();
    let cur = match tokio::task::spawn_blocking(move || {
        proxies::test_proxy_delay(&now_clone, None, DELAY_TIMEOUT)
    })
    .await
    {
        Ok(Ok(Some(d))) => Some(d),
        _ => None,
    };
    let cur_txt = match cur {
        Some(d) => format!("{d}ms"),
        None => "unreachable".to_owned(),
    };

    if let Some(d) = cur {
        if d <= THRESHOLD_MS {
            set_status(format!("{GROUP}: {now} {d}ms"));
            return;
        }
    }

    let others: Vec<String> = all.into_iter().filter(|n| n != &now).collect();
    if others.is_empty() {
        set_status(format!("{GROUP}: {now} bad ({cur_txt}), no other nodes to fail over"));
        return;
    }

    let mut tasks = Vec::with_capacity(others.len());
    let sem = std::sync::Arc::new(tokio::sync::Semaphore::new(8));
    for n in &others {
        let permit = match sem.clone().acquire_owned().await {
            Ok(p) => p,
            Err(_) => break,
        };
        let n = n.clone();
        tasks.push(tokio::task::spawn_blocking(move || {
            let r = proxies::test_proxy_delay(&n, None, DELAY_TIMEOUT);
            drop(permit);
            r
        }));
    }

    let mut best: Option<(String, u64)> = None;
    for (n, t) in others.iter().zip(tasks) {
        if let Ok(Ok(Some(d))) = t.await {
            if best.as_ref().is_none_or(|(_, bd)| d < *bd) {
                best = Some((n.clone(), d));
            }
        }
    }

    match best {
        Some((node, d)) => {
            let n = node.clone();
            let switched = tokio::task::spawn_blocking(move || proxies::select_proxy(GROUP, &n))
                .await;
            match switched {
                Ok(Ok(_)) => set_status(format!(
                    "{GROUP}: {now} bad ({cur_txt}) -> switched to {node} ({d}ms)"
                )),
                _ => set_status(format!("{GROUP}: {now} bad, switch to {node} FAILED")),
            }
        }
        None => set_status(format!("{GROUP}: {now} bad ({cur_txt}), all other nodes failed")),
    }
}
