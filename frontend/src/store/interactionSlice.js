import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { createInteraction, searchHcps } from '../api/client';

const initialFormState = {
  hcp_id: '',
  hcp_name: '',
  rep_id: 'demo-rep-id', // in production, pulled from auth context
  interaction_type: 'visit',
  occurred_at: new Date().toISOString().slice(0, 16),
  duration_minutes: 15,
  products_discussed: [],
  key_discussion_points: '',
  samples_distributed: [],
  hcp_sentiment: 'neutral',
  follow_up_needed: false,
  follow_up_notes: '',
  created_via: 'form',
};

export const submitInteraction = createAsyncThunk(
  'interaction/submit',
  async (payload, { rejectWithValue }) => {
    try {
      return await createInteraction(payload);
    } catch (err) {
      return rejectWithValue(err.response?.data || { message: err.message });
    }
  }
);

export const searchHcpOptions = createAsyncThunk(
  'interaction/searchHcps',
  async (query) => searchHcps(query)
);

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: {
    form: initialFormState,
    hcpOptions: [],
    submitStatus: 'idle', // idle | loading | succeeded | failed
    lastResult: null,
    error: null,
  },
  reducers: {
    updateField: (state, action) => {
      const { field, value } = action.payload;
      state.form[field] = value;
    },
    addProduct: (state, action) => {
      state.form.products_discussed.push(action.payload);
    },
    removeProduct: (state, action) => {
      state.form.products_discussed.splice(action.payload, 1);
    },
    resetForm: (state) => {
      state.form = initialFormState;
      state.submitStatus = 'idle';
      state.lastResult = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitInteraction.pending, (state) => {
        state.submitStatus = 'loading';
        state.error = null;
      })
      .addCase(submitInteraction.fulfilled, (state, action) => {
        state.submitStatus = 'succeeded';
        state.lastResult = action.payload;
      })
      .addCase(submitInteraction.rejected, (state, action) => {
        state.submitStatus = 'failed';
        state.error = action.payload;
      })
      .addCase(searchHcpOptions.fulfilled, (state, action) => {
        state.hcpOptions = action.payload;
      });
  },
});

export const { updateField, addProduct, removeProduct, resetForm } = interactionSlice.actions;
export default interactionSlice.reducer;
