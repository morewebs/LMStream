package lmstream

import (
	"encoding/binary"
)

type SettingsPayload struct {
	Version               uint8
	MaxFrameSize          uint32
	PauseBufferCap        uint32
	HeartbeatMs           uint32
	MaxConcurrentSessions uint16
}

func DecodeSettings(b []byte) (SettingsPayload, error) {
	if len(b) != 18 {
		return SettingsPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Settings length != 18"}
	}
	return SettingsPayload{
		Version:               b[0],
		MaxFrameSize:          binary.LittleEndian.Uint32(b[1:5]),
		PauseBufferCap:        binary.LittleEndian.Uint32(b[5:9]),
		HeartbeatMs:           binary.LittleEndian.Uint32(b[9:13]),
		MaxConcurrentSessions: binary.LittleEndian.Uint16(b[13:15]),
	}, nil
}

type UsagePayload struct {
	PromptTokens     uint32
	CompletionTokens uint32
	TotalTokens      uint32
	CachedTokens     uint32
	AttemptCount     uint8
}

func DecodeUsage(b []byte) (UsagePayload, error) {
	if len(b) != 20 {
		return UsagePayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Usage length != 20"}
	}
	if b[17] != 0 || binary.LittleEndian.Uint16(b[18:20]) != 0 {
		return UsagePayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Reserved field non-zero"}
	}
	return UsagePayload{
		PromptTokens:     binary.LittleEndian.Uint32(b[0:4]),
		CompletionTokens: binary.LittleEndian.Uint32(b[4:8]),
		TotalTokens:      binary.LittleEndian.Uint32(b[8:12]),
		CachedTokens:     binary.LittleEndian.Uint32(b[12:16]),
		AttemptCount:     b[16],
	}, nil
}

type MetricsPayload struct {
	TTFTMs          uint32
	TotalDurationMs uint32
	TokensPerSec    uint32
	ObfuscatedKeyID uint64
}

func DecodeMetrics(b []byte) (MetricsPayload, error) {
	if len(b) != 20 {
		return MetricsPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Metrics length != 20"}
	}
	return MetricsPayload{
		TTFTMs:          binary.LittleEndian.Uint32(b[0:4]),
		TotalDurationMs: binary.LittleEndian.Uint32(b[4:8]),
		TokensPerSec:    binary.LittleEndian.Uint32(b[8:12]),
		ObfuscatedKeyID: binary.LittleEndian.Uint64(b[12:20]),
	}, nil
}

type EndPayload struct {
	FinishReason FinishReason
	ChoiceIndex  uint8
}

func DecodeEnd(b []byte) (EndPayload, error) {
	if len(b) != 2 {
		return EndPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "End length != 2"}
	}
	return EndPayload{FinishReason: FinishReason(b[0]), ChoiceIndex: b[1]}, nil
}

type ErrorPayload struct {
	Code           ErrorCode
	UpstreamStatus uint16
	ChoiceIndex    uint8
	Scope          ErrorScope
	Message        string
}

func DecodeError(b []byte) (ErrorPayload, error) {
	if len(b) < 8 {
		return ErrorPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Error length < 8"}
	}
	code := ErrorCode(binary.LittleEndian.Uint16(b[0:2]))
	status := binary.LittleEndian.Uint16(b[2:4])
	choice := b[4]
	scope := ErrorScope(b[5])
	msgLen := binary.LittleEndian.Uint16(b[6:8])
	if len(b) < 8+int(msgLen) {
		return ErrorPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Truncated error message"}
	}
	return ErrorPayload{
		Code:           code,
		UpstreamStatus: status,
		ChoiceIndex:    choice,
		Scope:          scope,
		Message:        string(b[8 : 8+msgLen]),
	}, nil
}

type RewindPayload struct {
	TargetOpcode Opcode
	ChoiceIndex  uint8
	ByteOffset   uint32
}

func DecodeRewind(b []byte) (RewindPayload, error) {
	if len(b) != 8 {
		return RewindPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Rewind length != 8"}
	}
	if binary.LittleEndian.Uint16(b[2:4]) != 0 {
		return RewindPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "Rewind reserved non-zero"}
	}
	return RewindPayload{
		TargetOpcode: Opcode(b[0]),
		ChoiceIndex:  b[1],
		ByteOffset:   binary.LittleEndian.Uint32(b[4:8]),
	}, nil
}

type ToolCallPayload struct {
	ChoiceIndex uint8
	CallIndex   uint16
	Flags       uint8
	ID          string
	Name        string
	ArgsDelta   string
}

func DecodeToolCall(b []byte) (ToolCallPayload, error) {
	if len(b) < 4 {
		return ToolCallPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "ToolCall length < 4"}
	}
	choice := b[0]
	callIdx := binary.LittleEndian.Uint16(b[1:3])
	flags := b[3]
	if (flags & ToolFlagReservedMask) != 0 {
		return ToolCallPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "ToolCall reserved flags set"}
	}
	isStart := (flags & ToolFlagStart) != 0
	if isStart {
		if len(b) < 7 {
			return ToolCallPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "ToolCall START missing header"}
		}
		idLen := int(b[4])
		nameLen := int(binary.LittleEndian.Uint16(b[5:7]))
		if len(b) < 7+idLen+nameLen {
			return ToolCallPayload{}, &LMStreamError{Code: ErrorCodeProtocolViolation, Scope: ErrorScopeConnection, Message: "ToolCall truncated identifiers"}
		}
		id := string(b[7 : 7+idLen])
		name := string(b[7+idLen : 7+idLen+nameLen])
		args := string(b[7+idLen+nameLen:])
		return ToolCallPayload{ChoiceIndex: choice, CallIndex: callIdx, Flags: flags, ID: id, Name: name, ArgsDelta: args}, nil
	} else {
		return ToolCallPayload{ChoiceIndex: choice, CallIndex: callIdx, Flags: flags, ArgsDelta: string(b[4:])}, nil
	}
}
