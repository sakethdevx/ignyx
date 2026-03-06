use dashmap::DashMap;
use pyo3::prelude::*;
use std::sync::Arc;
use tokio::sync::broadcast;

/// Core PubSub engine bridging Python and native-Rust Tokio tasks.
#[pyclass(name = "PubSub")]
pub struct PubSub {
    /// Maps a channel name to its broadcast sender
    pub(crate) channels: Arc<DashMap<String, broadcast::Sender<String>>>,
}

impl Default for PubSub {
    fn default() -> Self {
        Self::new()
    }
}

#[pymethods]
impl PubSub {
    #[new]
    pub fn new() -> Self {
        Self {
            channels: Arc::new(DashMap::new()),
        }
    }

    /// Broadcast a message to all connected WebSockets on a given channel.
    /// This happens natively in Rust, waking up subscribers without acquiring the Python GIL
    /// for each connected client.
    /// Returns the number of active subscribers that received the message.
    pub fn broadcast(&self, channel: &str, message: String) -> PyResult<usize> {
        let count = if let Some(sender) = self.channels.get(channel) {
            match sender.send(message) {
                Ok(receivers) => receivers,
                Err(_) => 0, // No active receivers
            }
        } else {
            0
        };
        Ok(count)
    }
}

impl PubSub {
    /// Internal Rust method to subscribe to a channel
    pub(crate) fn subscribe(&self, channel: &str) -> broadcast::Receiver<String> {
        let sender = self
            .channels
            .entry(channel.to_string())
            .or_insert_with(|| {
                // max 1024 messages stored per channel for slow consumers
                // before they lag and are disconnected
                let (tx, _) = broadcast::channel(1024);
                tx
            });
        sender.subscribe()
    }
}
