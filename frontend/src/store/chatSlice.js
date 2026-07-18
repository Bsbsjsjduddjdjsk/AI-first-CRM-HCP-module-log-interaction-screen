import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { v4 as uuidv4 } from 'uuid';
import { sendChatMessage, confirmChatAction } from '../api/client';

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async (messageText, { getState, rejectWithValue }) => {
    const { session_id, rep_id } = getState().chat;
    try {
      return await sendChatMessage({ session_id, rep_id, message: messageText });
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: err.message });
    }
  }
);

export const confirmDraft = createAsyncThunk(
  'chat/confirmDraft',
  async ({ approved, editedPayload }, { getState, rejectWithValue }) => {
    const { session_id, rep_id } = getState().chat;
    try {
      return await confirmChatAction({
        session_id,
        rep_id,
        approved,
        edited_payload: editedPayload || null,
      });
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: err.message });
    }
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    session_id: uuidv4(),
    rep_id: 'demo-rep-id',
    messages: [], // { role: 'user' | 'agent', content: string }
    pendingPreview: null,
    requiresConfirmation: false,
    status: 'idle',
    error: null,
  },
  reducers: {
    resetChat: (state) => {
      state.session_id = uuidv4();
      state.messages = [];
      state.pendingPreview = null;
      state.requiresConfirmation = false;
      state.status = 'idle';
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.status = 'loading';
        state.messages.push({ role: 'user', content: action.meta.arg });
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = 'idle';
        state.messages.push({ role: 'agent', content: action.payload.agent_message });
        state.pendingPreview = action.payload.structured_preview || null;
        state.requiresConfirmation = action.payload.requires_confirmation;
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
        state.messages.push({
          role: 'agent',
          content: "Sorry, something went wrong reaching the agent. Please try again.",
        });
      })
      .addCase(confirmDraft.fulfilled, (state, action) => {
        state.requiresConfirmation = false;
        state.pendingPreview = null;
        const status = action.payload.status;
        state.messages.push({
          role: 'agent',
          content:
            status === 'logged' || status === 'updated'
              ? 'Saved to the CRM.'
              : 'Okay, discarded that.',
        });
      });
  },
});

export const { resetChat } = chatSlice.actions;
export default chatSlice.reducer;
