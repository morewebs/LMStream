pub const HEADER_SIZE: usize = 8;
pub const MAX_PAYLOAD_SIZE: usize = 65527;

#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Opcode {
    Open = 0x01,
    OpenAck = 0x02,
    Content = 0x03,
    Reasoning = 0x04,
    ToolCall = 0x05,
    Usage = 0x06,
    Metrics = 0x07,
    End = 0x08,
    Error = 0x09,
    Cancel = 0x0A,
    Pause = 0x0B,
    Resume = 0x0C,
    Steer = 0x0D,
    Rewind = 0x0E,
    Settings = 0x0F,
    Ping = 0x10,
    Pong = 0x11,
}

impl TryFrom<u8> for Opcode {
    type Error = LMStreamError;
    fn try_from(v: u8) -> Result<Self, LMStreamError> {
        match v {
            0x01 => Ok(Opcode::Open),
            0x02 => Ok(Opcode::OpenAck),
            0x03 => Ok(Opcode::Content),
            0x04 => Ok(Opcode::Reasoning),
            0x05 => Ok(Opcode::ToolCall),
            0x06 => Ok(Opcode::Usage),
            0x07 => Ok(Opcode::Metrics),
            0x08 => Ok(Opcode::End),
            0x09 => Ok(Opcode::Error),
            0x0A => Ok(Opcode::Cancel),
            0x0B => Ok(Opcode::Pause),
            0x0C => Ok(Opcode::Resume),
            0x0D => Ok(Opcode::Steer),
            0x0E => Ok(Opcode::Rewind),
            0x0F => Ok(Opcode::Settings),
            0x10 => Ok(Opcode::Ping),
            0x11 => Ok(Opcode::Pong),
            _ => Err(LMStreamError {
                code: 1008,
                scope: "connection".to_string(),
                message: format!("Unknown or unassigned core opcode: 0x{:02x}", v),
            }),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LMStreamError {
    pub code: u16,
    pub scope: String,
    pub message: String,
}

impl std::fmt::Display for LMStreamError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "[LMStream {} ERROR {}] {}", self.scope.to_uppercase(), self.code, self.message)
    }
}

impl std::error::Error for LMStreamError {}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrameHeader {
    pub stream_id: u32,
    pub opcode: Opcode,
    pub flags: u8,
    pub length: u16,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Frame {
    pub header: FrameHeader,
    pub payload: Vec<u8>,
}

pub fn encode_header(h: &FrameHeader) -> Result<Vec<u8>, LMStreamError> {
    if h.length as usize > MAX_PAYLOAD_SIZE {
        return Err(LMStreamError {
            code: 1008,
            scope: "connection".to_string(),
            message: "Payload length exceeds maximum cap".to_string(),
        });
    }
    let mut buf = Vec::with_capacity(HEADER_SIZE);
    buf.extend_from_slice(&h.stream_id.to_le_bytes());
    buf.push(h.opcode as u8);
    buf.push(h.flags);
    buf.extend_from_slice(&h.length.to_le_bytes());
    Ok(buf)
}

pub fn decode_header(b: &[u8]) -> Result<FrameHeader, LMStreamError> {
    if b.len() < HEADER_SIZE {
        return Err(LMStreamError {
            code: 1008,
            scope: "connection".to_string(),
            message: "Header buffer too short".to_string(),
        });
    }
    let stream_id = u32::from_le_bytes(b[0..4].try_into().unwrap());
    let op_raw = b[4];
    let flags = b[5];
    let length = u16::from_le_bytes(b[6..8].try_into().unwrap());

    if length as usize > MAX_PAYLOAD_SIZE {
        return Err(LMStreamError {
            code: 1008,
            scope: "connection".to_string(),
            message: "Length exceeds cap".to_string(),
        });
    }

    if (flags & 0xFE) != 0 {
        return Err(LMStreamError {
            code: 1008,
            scope: "connection".to_string(),
            message: "Reserved flags non-zero".to_string(),
        });
    }

    let opcode = Opcode::try_from(op_raw)?;

    let is_conn = matches!(opcode, Opcode::Settings | Opcode::Ping | Opcode::Pong | Opcode::Error);
    if stream_id == 0 && !is_conn {
        return Err(LMStreamError {
            code: 1008,
            scope: "connection".to_string(),
            message: "Data opcode on StreamID 0".to_string(),
        });
    }
    if stream_id != 0 && matches!(opcode, Opcode::Settings | Opcode::Ping | Opcode::Pong) {
        return Err(LMStreamError {
            code: 1008,
            scope: "connection".to_string(),
            message: "Control opcode on non-zero StreamID".to_string(),
        });
    }

    // Fixed payload length validation
    let req_len = match opcode {
        Opcode::Settings => Some(18),
        Opcode::Ping => Some(8),
        Opcode::Pong => Some(8),
        Opcode::Usage => Some(20),
        Opcode::Metrics => Some(20),
        Opcode::End => Some(2),
        Opcode::Cancel => Some(0),
        Opcode::Pause => Some(0),
        Opcode::Resume => Some(0),
        Opcode::Rewind => Some(8),
        _ => None,
    };

    if let Some(expected) = req_len {
        if length as usize != expected {
            return Err(LMStreamError {
                code: 1008,
                scope: "connection".to_string(),
                message: format!("Fixed length mismatch for opcode 0x{:02x}", op_raw),
            });
        }
    }

    Ok(FrameHeader { stream_id, opcode, flags, length })
}

pub fn encode_frame(f: &Frame) -> Result<Vec<u8>, LMStreamError> {
    let mut h = f.header.clone();
    h.length = f.payload.len() as u16;
    let mut bytes = encode_header(&h)?;
    bytes.extend_from_slice(&f.payload);
    Ok(bytes)
}

pub fn decode_frame(b: &[u8]) -> Result<Frame, LMStreamError> {
    let h = decode_header(b)?;
    let total = HEADER_SIZE + h.length as usize;
    if b.len() < total {
        return Err(LMStreamError {
            code: 1008,
            scope: "connection".to_string(),
            message: "Truncated payload".to_string(),
        });
    }
    Ok(Frame { header: h, payload: b[HEADER_SIZE..total].to_vec() })
}

pub fn validate_payload(opcode: Opcode, payload: &[u8]) -> Result<(), LMStreamError> {
    match opcode {
        Opcode::Usage => {
            if payload.len() != 20 {
                return Err(LMStreamError { code: 1008, scope: "connection".into(), message: "Usage len != 20".into() });
            }
            if payload[17] != 0 || u16::from_le_bytes(payload[18..20].try_into().unwrap()) != 0 {
                return Err(LMStreamError { code: 1008, scope: "connection".into(), message: "Usage reserved non-zero".into() });
            }
        }
        Opcode::Rewind => {
            if payload.len() != 8 {
                return Err(LMStreamError { code: 1008, scope: "connection".into(), message: "Rewind len != 8".into() });
            }
            if u16::from_le_bytes(payload[2..4].try_into().unwrap()) != 0 {
                return Err(LMStreamError { code: 1008, scope: "connection".into(), message: "Rewind reserved non-zero".into() });
            }
        }
        Opcode::Error => {
            if payload.len() < 8 {
                return Err(LMStreamError { code: 1008, scope: "connection".into(), message: "Error len < 8".into() });
            }
            let msg_len = u16::from_le_bytes(payload[6..8].try_into().unwrap()) as usize;
            if payload.len() < 8 + msg_len {
                return Err(LMStreamError { code: 1008, scope: "connection".into(), message: "Truncated error msg".into() });
            }
        }
        _ => {}
    }
    Ok(())
}
