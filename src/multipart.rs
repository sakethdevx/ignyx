use std::collections::HashMap;
use bytes::Bytes;
use futures_util::stream::StreamExt;

pub(crate) async fn parse_multipart(
    content_type: &str,
    body_bytes: &[u8],
    form_fields: &mut HashMap<String, String>,
    form_files: &mut HashMap<String, (String, String, Vec<u8>)>,
) {
    if let Some(boundary) = multer::parse_boundary(content_type).ok() {
        let bytes_clone = body_bytes.to_vec();
        let stream = futures_util::stream::once(async move {
            Ok::<Bytes, std::convert::Infallible>(Bytes::from(bytes_clone))
        });
        let mut multipart = multer::Multipart::new(stream, boundary);
        while let Some(mut field) = multipart.next_field().await.unwrap_or(None) {
            let name = field.name().unwrap_or("").to_string();
            if let Some(filename_ref) = field.file_name() {
                let filename = filename_ref.to_string();
                let c_type = field.content_type().map(|c| c.to_string()).unwrap_or_else(|| "application/octet-stream".to_string());
                let data = field.bytes().await.unwrap_or_default().to_vec();
                form_files.insert(name, (filename, c_type, data));
            } else {
                let text = field.text().await.unwrap_or_default();
                form_fields.insert(name, text);
            }
        }
    }
}
