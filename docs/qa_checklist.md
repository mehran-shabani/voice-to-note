# VoiceNote App - Manual QA Checklist

## Test Environment Setup
- [ ] Flutter SDK installed (version 3.0+)
- [ ] Android device/emulator running (API 21+)
- [ ] Backend server running and accessible
- [ ] Update `UPLOAD_ENDPOINT` in `/lib/constants/app_constants.dart` to your server URL

## 1. Recording Functionality

### 1.1 Basic Recording
- [ ] Launch app - recording controls should be centered
- [ ] Tap red microphone button - recording should start
- [ ] Verify timer starts counting from 00:00
- [ ] Verify "Recording..." status appears in red
- [ ] Verify remaining time countdown displays correctly

### 1.2 Pause/Resume
- [ ] While recording, tap pause button - recording should pause
- [ ] Verify timer stops incrementing
- [ ] Verify status changes to "Paused" in orange
- [ ] Tap play button - recording should resume
- [ ] Verify timer continues from where it paused

### 1.3 Stop Recording
- [ ] Tap stop button - recording should stop
- [ ] Verify timer resets to 00:00
- [ ] Verify "Edit Last Recording" button appears
- [ ] Verify "Upload" button appears with filename

### 1.4 Auto-Stop at 5 Minutes
- [ ] Start a new recording
- [ ] Let it run for 5 minutes
- [ ] Verify recording automatically stops at 5:00
- [ ] Verify file is saved with correct timestamp

### 1.5 File Verification
- [ ] Check saved file location: `Android/data/com.example.voicenote/files/recordings/`
- [ ] Verify filename format: `voicenote_YYYY-MM-DD_HH-mm-ss.m4a`
- [ ] Verify file size is approximately 4MB per minute (~20MB for 5 minutes)
- [ ] Verify audio codec is AAC at 64kbps (use media info tool)

## 2. Editor Functionality

### 2.1 Load Recording
- [ ] After recording, tap "Edit Last Recording"
- [ ] Verify editor panel opens on the left
- [ ] Verify file name and duration are displayed correctly

### 2.2 Selection
- [ ] Enter start time (e.g., 2 seconds)
- [ ] Enter end time (e.g., 5 seconds)
- [ ] Tap "Set Selection"
- [ ] Verify selection range is displayed in blue info card

### 2.3 Cut Operation
- [ ] With valid selection, tap "Cut" button
- [ ] Verify "Cut successful" message appears
- [ ] Verify edit appears in "Edit History" section
- [ ] Verify audio duration is reduced by cut amount

### 2.4 Undo Operation
- [ ] After cutting, tap "Undo" button
- [ ] Verify "Undo successful" message appears
- [ ] Verify edit is removed from history
- [ ] Verify original duration is restored

### 2.5 Multiple Cuts
- [ ] Perform first cut (e.g., 2-5 seconds)
- [ ] Perform second cut (e.g., 10-15 seconds)
- [ ] Verify both cuts appear in edit history
- [ ] Undo once - verify only last cut is undone
- [ ] Undo again - verify both cuts are undone

### 2.6 Save Edited File
- [ ] After making cuts, tap "Save Edited"
- [ ] Verify success message with new filename
- [ ] Verify filename format: `voicenote_YYYY-MM-DD_HH-mm-ss_edited.m4a`
- [ ] Verify editor panel closes
- [ ] Verify new file appears as "last recording"

### 2.7 Non-Destructive Editing
- [ ] Check original file still exists unchanged
- [ ] Verify edited file is a separate file

## 3. Upload Functionality

### 3.1 Basic Upload
- [ ] With a recording available, tap "Upload" button
- [ ] Verify upload progress bar appears
- [ ] Verify percentage updates during upload
- [ ] Verify success toast appears with status code
- [ ] Verify "Upload successful! (201)" or "(200)" message

### 3.2 Upload Cancel
- [ ] Start an upload
- [ ] Tap "Cancel" during upload
- [ ] Verify upload is cancelled
- [ ] Verify UI returns to idle state

### 3.3 Network Error Handling
- [ ] Turn off network/use wrong server URL
- [ ] Attempt upload
- [ ] Verify appropriate error message appears
- [ ] Verify UI returns to idle state after 3 seconds

### 3.4 Server Response Codes
- [ ] Verify app accepts 201 Created response
- [ ] Verify app accepts 200 OK response
- [ ] Test with invalid file format - verify 400 error handling
- [ ] Test with oversized file - verify 413 error handling

### 3.6 End-to-End Flow (Record → Cut → Undo → Upload)
- [ ] Record ≤ 20s sample
- [ ] Perform a cut (e.g., remove 2–4s)
- [ ] Undo the cut and verify duration restored
- [ ] Upload the file and verify success toast and Location header

### 3.5 Request Verification
- [ ] Use network inspector/proxy to verify request
- [ ] Verify request is `multipart/form-data`
- [ ] Verify field name is `audio`
- [ ] Verify filename is included in request
- [ ] Verify Content-Type headers are correct

## 4. Edge Cases & Error Handling

### 4.1 Permissions
- [ ] Deny microphone permission initially
- [ ] Try to record - verify permission request
- [ ] Deny again - verify appropriate error handling

### 4.2 Storage
- [ ] Fill device storage near capacity
- [ ] Try to record - verify storage error handling
- [ ] Try to save edited file - verify error handling

### 4.3 Invalid Editor Input
- [ ] Enter negative values for selection
- [ ] Enter end time before start time
- [ ] Enter time beyond file duration
- [ ] Verify appropriate validation messages

### 4.4 Concurrent Operations
- [ ] Try to start new recording while uploading
- [ ] Try to edit while uploading
- [ ] Verify operations don't interfere

## 5. UI/UX Verification

### 5.1 Visual Elements
- [ ] Recording button is prominent and centered
- [ ] Timer is large and readable
- [ ] Progress indicators are smooth
- [ ] Colors match states (red=recording, orange=paused, etc.)

### 5.2 Responsiveness
- [ ] All buttons provide immediate feedback
- [ ] No UI freezing during operations
- [ ] Smooth animations and transitions

### 5.3 Error Messages
- [ ] Error messages are clear and actionable
- [ ] Success messages are positive and informative
- [ ] Messages auto-dismiss appropriately

## Test Completion Checklist
- [ ] Recorded at least 3 different audio files
- [ ] Successfully edited and saved at least 2 files
- [ ] Successfully uploaded at least 2 files
- [ ] Tested all error scenarios
- [ ] Verified file formats and sizes
- [ ] Confirmed non-destructive editing

## Known Limitations
- Android only (iOS not supported)
- Single-level undo only
- No waveform visualization during selection
- No audio preview/playback in editor
- Fixed 5-minute maximum recording time

## Notes for Testers
- Server URL must be configured before testing upload
- Ensure device has sufficient storage (>100MB free)
- Test with both short (30s) and long (5min) recordings
- Verify behavior with both edited and unedited files