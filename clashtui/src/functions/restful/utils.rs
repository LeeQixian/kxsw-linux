use super::*;

pub fn request(
    method: minreq::Method,
    sub_url: &str,
    payload: Option<String>,
) -> Result<minreq::Response> {
    let controller = crate::config::API_ADDR;
    let mut req = minreq::Request::new(method, format!("{controller}{sub_url}"));
    if let Some(kv) = payload {
        req = req
            .with_header("Content-Type", "application/json")
            .with_body(kv);
    }
    if let Some(s) = crate::config::API_SECRET {
        req = req.with_header(headers::AUTHORIZATION, format!("Bearer {s}"));
    }
    req.with_timeout(crate::config::API_TIMEOUT).send()
}
