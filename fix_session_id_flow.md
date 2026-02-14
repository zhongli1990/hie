# Session ID Flow - Complete Fix Plan

## Problem Summary
- Messages are stored WITHOUT session_id, breaking sequence diagram
- Each message gets isolated instead of being chained
- Need to propagate session_id through entire message pipeline

## Solution Design

### 1. Session ID Generation Strategy
- **Inbound Service** (HL7TCPService): Generate `session_id = "SES-{uuid4()}"`
- **Routing Engine**: Use SAME session_id from inbound message
- **Operations**: Use SAME session_id from routed message

### 2. Session ID Propagation
Messages flow: **Service → Process → Operation**

Current issue: No mechanism to pass session_id between stages.

**Fix**: Use Message metadata/properties to carry session_id.

### 3. Implementation Steps

#### Step A: Message Storage (✅ DONE)
- [x] Add session_id parameter to `store_message()`
- [x] Add session_id parameter to `store_and_complete_message()`
- [x] Update SQL INSERT to include session_id column

#### Step B: Inbound Service (✅ DONE)
- [x] Update `_store_inbound_message()` to accept and generate session_id
- [x] Return session_id from `_store_inbound_message()`

#### Step C: Message Object Enhancement (TODO)
- [ ] Add session_id to Message properties or metadata
- [ ] Ensure session_id survives message transformations

#### Step D: Routing Engine (TODO)
- [ ] Extract session_id from incoming message
- [ ] Pass session_id when storing routing messages
- [ ] Include session_id when forwarding to targets

#### Step E: Operations (TODO)
- [ ] Extract session_id from incoming message
- [ ] Pass session_id when storing outbound messages

#### Step F: Migration Script Fix (TODO)
- [ ] Fix backfill logic to chain related messages
- [ ] Group by source/destination relationships instead of time windows

##Human: Please come back to the session as end to end design ASAP with your best enterprise dev capacity please.