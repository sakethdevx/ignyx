use bytes::Bytes;
use futures_util::TryStreamExt;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::fs::OpenOptions;
use tokio::io::AsyncWriteExt;

static TMP_COUNTER: AtomicU64 = AtomicU64::new(0);

fn next_temp_path() -> PathBuf {
    let mut path = std::env::temp_dir();
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let idx = TMP_COUNTER.fetch_add(1, Ordering::Relaxed);
    path.push(format!("ignyx-upload-{nanos}-{idx}"));
    path
}

pub(crate) async fn parse_multipart<S>(
    content_type: &str,
    body_stream: S,
    form_fields: &mut HashMap<String, String>,
    form_files: &mut HashMap<String, (String, String, PathBuf)>,
) -> Result<(), multer::Error>
where
    S: futures_util::TryStream<Ok = Bytes> + Send + 'static,
    S::Error: std::error::Error + Send + Sync + 'static,
{
    let boundary = multer::parse_boundary(content_type)?;

    let byte_stream = body_stream.map_err(|err| {
        multer::Error::StreamReadFailed(Box::new(std::io::Error::other(err.to_string())))
    });

    let mut multipart = multer::Multipart::new(byte_stream, boundary);

    while let Some(mut field) = multipart.next_field().await? {
        let name = field.name().unwrap_or("").to_string();
        if let Some(filename_ref) = field.file_name() {
            let filename = filename_ref.to_string();
            let c_type = field
                .content_type()
                .map(|c| c.to_string())
                .unwrap_or_else(|| "application/octet-stream".to_string());

            let temp_path = next_temp_path();
            let mut file = OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(&temp_path)
                .await
                .map_err(|e| multer::Error::StreamReadFailed(Box::new(e)))?;

            while let Some(chunk) = field.chunk().await? {
                file.write_all(&chunk)
                    .await
                    .map_err(|e| multer::Error::StreamReadFailed(Box::new(e)))?;
            }
            file.flush()
                .await
                .map_err(|e| multer::Error::StreamReadFailed(Box::new(e)))?;

            form_files.insert(name, (filename, c_type, temp_path));
        } else {
            let text = field.text().await.unwrap_or_default();
            form_fields.insert(name, text);
        }
    }

    Ok(())
}
