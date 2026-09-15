package lmstream

type Opcode uint8

const (
	OpcodeOpen      Opcode = 0x01
	OpcodeOpenAck   Opcode = 0x02
	OpcodeContent   Opcode = 0x03
	OpcodeReasoning Opcode = 0x04
	OpcodeToolCall  Opcode = 0x05
	OpcodeUsage     Opcode = 0x06
	OpcodeMetrics   Opcode = 0x07
	OpcodeEnd       Opcode = 0x08
	OpcodeError     Opcode = 0x09
	OpcodeCancel    Opcode = 0x0A
	OpcodePause     Opcode = 0x0B
	OpcodeResume    Opcode = 0x0C
	OpcodeSteer     Opcode = 0x0D
	OpcodeRewind    Opcode = 0x0E
	OpcodeSettings  Opcode = 0x0F
	OpcodePing      Opcode = 0x10
	OpcodePong      Opcode = 0x11
)

const (
	HeaderFlagBoundary     uint8 = 0x01
	HeaderFlagCompressed   uint8 = 0x02
	HeaderFlagReservedMask uint8 = 0xFE
)

const (
	ToolFlagStart        uint8 = 0x01
	ToolFlagCont         uint8 = 0x02
	ToolFlagEnd          uint8 = 0x04
	ToolFlagReservedMask uint8 = 0xF8
)

type FinishReason uint8

const (
	FinishReasonStop          FinishReason = 0x00
	FinishReasonLength        FinishReason = 0x01
	FinishReasonToolCalls     FinishReason = 0x02
	FinishReasonContentFilter FinishReason = 0x03
	FinishReasonCancelled     FinishReason = 0x04
)

type ErrorCode uint16

const (
	ErrorCodeBadRequest        ErrorCode = 1001
	ErrorCodeAuthFailed        ErrorCode = 1002
	ErrorCodeRateLimited       ErrorCode = 1003
	ErrorCodeModelOverloaded   ErrorCode = 1004
	ErrorCodeUpstreamError     ErrorCode = 1005
	ErrorCodeBufferOverflow    ErrorCode = 1006
	ErrorCodeInvalidState      ErrorCode = 1007
	ErrorCodeProtocolViolation ErrorCode = 1008
	ErrorCodeSessionExpired    ErrorCode = 1009
)

type ErrorScope uint8

const (
	ErrorScopeSession    ErrorScope = 0x00
	ErrorScopeConnection ErrorScope = 0x01
)
