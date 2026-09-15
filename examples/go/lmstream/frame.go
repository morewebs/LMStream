package lmstream

import (
	"encoding/binary"
	"fmt"
)

const (
	HeaderSize     = 8
	MaxPayloadSize = 65527
)

type LMStreamError struct {
	Code    ErrorCode
	Scope   ErrorScope
	Message string
}

func (e *LMStreamError) Error() string {
	scopeStr := "SESSION"
	if e.Scope == ErrorScopeConnection {
		scopeStr = "CONNECTION"
	}
	return fmt.Sprintf("[LMStream %s ERROR %d] %s", scopeStr, e.Code, e.Message)
}

type FrameHeader struct {
	StreamID uint32
	Opcode   Opcode
	Flags    uint8
	Length   uint16
}

type Frame struct {
	Header  FrameHeader
	Payload []byte
}

func EncodeHeader(h FrameHeader) ([]byte, error) {
	if int(h.Length) > MaxPayloadSize {
		return nil, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Length exceeds cap"}
	}
	buf := make([]byte, HeaderSize)
	binary.LittleEndian.PutUint32(buf[0:4], h.StreamID)
	buf[4] = uint8(h.Opcode)
	buf[5] = h.Flags
	binary.LittleEndian.PutUint16(buf[6:8], h.Length)
	return buf, nil
}

func DecodeHeader(b []byte) (FrameHeader, error) {
	if len(b) < HeaderSize {
		return FrameHeader{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Header too short"}
	}
	streamID := binary.LittleEndian.Uint32(b[0:4])
	opRaw := b[4]
	flags := b[5]
	length := binary.LittleEndian.Uint16(b[6:8])

	if int(length) > MaxPayloadSize {
		return FrameHeader{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Length exceeds cap"}
	}

	if (flags & HeaderFlagReservedMask) != 0 {
		return FrameHeader{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Reserved flags set"}
	}

	op := Opcode(opRaw)
	isKnownCore := opRaw >= 0x01 && opRaw <= 0x11
	if !isKnownCore && opRaw <= 0x2F {
		return FrameHeader{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Unknown core opcode"}
	}

	isConn := op == OpcodeSettings || op == OpcodePing || op == OpcodePong || op == OpcodeError
	if streamID == 0 && !isConn {
		return FrameHeader{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Data opcode on StreamID 0"}
	}
	if streamID != 0 && (op == OpcodeSettings || op == OpcodePing || op == OpcodePong) {
		return FrameHeader{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Control opcode on non-zero stream"}
	}

	// Fixed length validation
	fixedLengths := map[Opcode]int{
		OpcodeSettings: 18,
		OpcodePing:     8,
		OpcodePong:     8,
		OpcodeUsage:    20,
		OpcodeMetrics:  20,
		OpcodeEnd:      2,
		OpcodeCancel:   0,
		OpcodePause:    0,
		OpcodeResume:   0,
		OpcodeRewind:   8,
	}
	if reqLen, ok := fixedLengths[op]; ok && int(length) != reqLen {
		return FrameHeader{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Fixed length mismatch"}
	}

	return FrameHeader{StreamID: streamID, Opcode: op, Flags: flags, Length: length}, nil
}

func EncodeFrame(f Frame) ([]byte, error) {
	f.Header.Length = uint16(len(f.Payload))
	hBytes, err := EncodeHeader(f.Header)
	if err != nil {
		return nil, err
	}
	return append(hBytes, f.Payload...), nil
}

func DecodeFrame(b []byte) (Frame, error) {
	h, err := DecodeHeader(b)
	if err != nil {
		return Frame{}, err
	}
	total := HeaderSize + int(h.Length)
	if len(b) < total {
		return Frame{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Truncated payload"}
	}
	return Frame{Header: h, Payload: b[HeaderSize:total]}, nil
}
