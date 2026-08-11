use minreq::Method;

pub mod config_struct;
#[macro_use]
mod utils;

use utils::*;

mod headers {
    pub const AUTHORIZATION: &str = "authorization";
}

type Result<T, E = minreq::Error> = core::result::Result<T, E>;

pub mod control {
    use super::*;

    /// Get clash core version
    ///
    /// for mihomo, it's like `{"meta": true, "version": "v1.1.1"}`
    pub fn version() -> Result<String> {
        request(Method::Get, "/version", None).and_then(|r| r.as_str().map(|s| s.to_owned()))
    }
}

pub mod config {
    use super::*;

    pub fn fetch() -> Result<config_struct::ClashConfig> {
        request(Method::Get, "/configs", None).and_then(|r| r.json())
    }

}

pub mod proxies;

pub mod connection {
    use super::*;

    use serde::Deserialize;

    #[cfg_attr(test, derive(Debug))]
    #[derive(Deserialize, Default)]
    #[serde(rename_all = "camelCase", default)]
    pub struct ConnInfo {
        pub download_total: u64,
        pub upload_total: u64,
        pub connections: Option<Vec<Conn>>,
    }

    #[cfg_attr(test, derive(Debug, Clone))]
    #[derive(Deserialize)]
    pub struct Conn {
        pub id: String,
        pub metadata: ConnMetaData,
        pub upload: u64,
        pub download: u64,
        #[allow(dead_code)]
        pub start: String,
        pub chains: Vec<String>,
        #[serde(default)]
        pub rule: Option<String>,
        #[allow(dead_code)]
        #[serde(default, rename = "rulePayload")]
        pub rule_payload: Option<String>,
    }

    #[cfg_attr(test, derive(Debug, Clone))]
    #[derive(Deserialize)]
    #[serde(rename_all = "camelCase")]
    pub struct ConnMetaData {
        #[cfg_attr(not(test), allow(dead_code))]
        pub network: String,
        #[serde(rename = "type", default)]
        #[allow(dead_code)]
        pub ctype: String,
        pub host: String,
        #[serde(default)]
        #[allow(dead_code)]
        pub process: String,
        #[serde(default)]
        #[cfg_attr(not(test), allow(dead_code))]
        pub process_path: String,

        #[serde(rename = "sourceIP")]
        #[allow(dead_code)]
        pub source_ip: String,
        #[allow(dead_code)]
        pub source_port: String,
        #[serde(default)]
        pub remote_destination: String,
        #[serde(default, rename = "destinationPort")]
        pub destination_port: String,
        #[serde(default, rename = "destinationIP")]
        pub destination_ip: Option<String>,
        #[allow(dead_code)]
        #[serde(default, rename = "sniffHost")]
        pub sniff_host: Option<String>,
    }

    /// return [ConnInfo]
    pub fn get_connections() -> Result<ConnInfo> {
        request(Method::Get, "/connections", None).and_then(|r| r.json())
    }

    /// Terminate all active connections
    pub fn terminate_all_connections() -> Result<()> {
        request(Method::Delete, "/connections", None).map(|_| ())
    }

    /// if `id` is some, will try to terminate that connection,
    /// otherwise try to terminate **all** connections.
    ///
    /// Return true on success
    ///
    /// NOTE:
    /// Empty str is returned if connection is terminated successfully
    pub fn terminate_connection(id: Option<String>) -> Result<bool> {
        request(
            Method::Delete,
            &format!(
                "/connections{}",
                id.map(|c| format!("/{c}")).unwrap_or_default()
            ),
            None,
        )
        .and_then(|r| {
            r.as_str().map(|s| {
                // try to catch failure
                log::debug!("terminate conn:{s}");
                s.is_empty()
            })
        })
    }
}

pub mod api_log {

    pub struct LogEntry {
        pub type_: String,
        pub payload: String,
        pub time: String,
    }

    pub(crate) fn timestamp() -> String {
        let secs = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs() as i64;
        let days = secs / 86400;
        let time_of_day = secs % 86400;
        let hh = time_of_day / 3600;
        let mm = (time_of_day % 3600) / 60;
        let ss = time_of_day % 60;

        let mut y: i64 = 1970;
        let mut remaining_days = days;
        loop {
            let days_in_year = if is_leap(y) { 366 } else { 365 };
            if remaining_days < days_in_year {
                break;
            }
            remaining_days -= days_in_year;
            y += 1;
        }
        let dims: &[i64] = if is_leap(y) {
            &[31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        } else {
            &[31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        };
        let mut mo = 1;
        for dim in dims {
            if remaining_days < *dim {
                break;
            }
            remaining_days -= dim;
            mo += 1;
        }
        let yy = y % 100;
        let dd = remaining_days + 1;
        format!("{yy:02}-{mo:02}-{dd:02} {hh:02}:{mm:02}:{ss:02}")
    }

    fn is_leap(y: i64) -> bool {
        (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0)
    }

    #[cfg_attr(not(test), allow(dead_code))]
    pub fn parse_log_entries(body: &str) -> Vec<LogEntry> {
        body.lines()
            .filter(|line| !line.is_empty())
            .filter_map(
                |line| match serde_json::from_str::<serde_json::Value>(line) {
                    Ok(v) => {
                        let type_ = v
                            .get("type")
                            .and_then(|t| t.as_str())
                            .unwrap_or("unknown")
                            .to_owned();
                        let payload = v
                            .get("payload")
                            .and_then(|p| p.as_str())
                            .unwrap_or("")
                            .to_owned();
                        Some(LogEntry {
                            type_,
                            payload,
                            time: timestamp(),
                        })
                    }
                    Err(_) => {
                        log::warn!("Failed to parse log line as JSON: {line}");
                        None
                    }
                },
            )
            .collect()
    }
}

#[cfg(test)]
mod connection_tests {
    use super::connection::*;

    fn load_singbox_connections() -> ConnInfo {
        let path = concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/tests/apidata/sing-box/connections.json"
        );
        let data = std::fs::read_to_string(path).unwrap();
        serde_json::from_str(&data).unwrap()
    }

    #[test]
    fn singbox_conninfo_totals() {
        let info = load_singbox_connections();
        assert!(info.download_total > 0);
        assert!(info.upload_total > 0);
    }

    #[test]
    fn singbox_connections_has_entries() {
        let info = load_singbox_connections();
        let conns = info.connections.expect("connections missing");
        assert!(!conns.is_empty());
    }

    #[test]
    fn singbox_conn_has_chains() {
        let info = load_singbox_connections();
        let conn = &info.connections.unwrap()[0];
        assert!(!conn.chains.is_empty());
    }

    #[test]
    fn singbox_conn_metadata_empty_process_path() {
        let info = load_singbox_connections();
        for conn in info.connections.unwrap() {
            assert_eq!(conn.metadata.process_path, "");
        }
    }

    #[test]
    fn singbox_conn_rule_is_some() {
        let info = load_singbox_connections();
        for conn in info.connections.unwrap() {
            assert!(conn.rule.is_some());
        }
    }

    #[test]
    fn singbox_conn_udp_connection() {
        let info = load_singbox_connections();
        let conns = info.connections.unwrap();
        let udp = conns
            .iter()
            .find(|c| c.metadata.network == "udp")
            .expect("UDP connection missing");
        assert_eq!(udp.metadata.destination_port, "53");
        assert_eq!(udp.metadata.host, "");
    }

    #[test]
    fn singbox_conn_has_destination_ip() {
        let info = load_singbox_connections();
        let conns = info.connections.unwrap();
        assert!(conns[0].metadata.destination_ip.is_some());
    }
}
