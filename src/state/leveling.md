# App Leveling & Stage Progression

This document outlines the structured progression for the auditory training application. The system is designed to be invisible to the user, providing a behind-the-scenes framework for the AI coach to guide the user's development.

## Initial Diagnostic Assessment (10 minutes)

**Diagnostic Structure:**
Tests user across 4 progressive complexity scenarios to determine starting stage:

**Diagnostic 1**: Single environmental sound (rain) - can user identify and describe basic characteristics?
**Diagnostic 2**: Environmental + individual speaker - can user process both simultaneously?
**Diagnostic 3**: Two conversations - can user track multiple speech streams?
**Diagnostic 4**: Three-stream mix (environment + music + speaker) - maximum complexity test

**Placement Logic:**

- Pass all 4: Start at stage 8
- Pass 3: Start at stage 6
- Pass 2: Start at stage 4
- Pass 1: Start at stage 2
- Pass 0: Start at stage 1

## Stage Progression (12 stages)

### Foundation Phase (stages 1-4)

**Stage 1: Single Stream Focus**

- **Audio Elements**: 1 Background Environmental (rotating: rain, birds, street, city)
- **Duration**: 6 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Correctly identify environmental sound type
  - Notice and report any volume changes
  - Maintain attention without significant distraction
- **Voice Agent Guidance**: "Describe what you're hearing" / "Has anything changed?" / "Focus on the details of this sound"

**Stage 2: Dual Stream Introduction**

- **Audio Elements**: 1 Noise Source + 1 Background Environmental
- **Duration**: 7 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Identify both sound types correctly
  - Determine which sound is more prominent
  - Switch focus between sounds when agent requests
- **Voice Agent Guidance**: "Now listen to the other sound" / "Can you focus on the background noise?" / "Tell me about both sounds you hear"

**Stage 3: Speech in Environment**

- **Audio Elements**: 1 Background Environmental + 1 Individual Speaker
- **Duration**: 7 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Follow speaker's content while environmental sound continues
  - Answer questions about what speaker discussed
  - Switch attention between speaker and environment on command
- **Voice Agent Guidance**: "Focus on what the person is saying" / "Now pay attention to the background" / "Can you tell me what they just talked about?"

**Stage 4: Competing Speech**

- **Audio Elements**: 2 Individual Speakers (different topics)
- **Duration**: 8 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Track both speakers' topics separately
  - Switch focus between speakers when requested
  - Answer specific questions about either speaker's content
- **Voice Agent Guidance**: "Listen to the first speaker" / "Now focus on the second speaker" / "What did the first person say about [topic]?"

### Parallel Processing Phase (stages 5-8)

**Stage 5: Triple Stream Management**

- **Audio Elements**: 1 Background Environmental + 1 Instrumental Music + 1 Individual Speaker
- **Duration**: 8 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Maintain awareness of all three audio streams
  - Focus on specific stream when agent requests
  - Answer questions about any stream's content
- **Voice Agent Guidance**: "Focus on the music now" / "What is the speaker explaining?" / "Describe the background sounds"

**Stage 6: Complex Environmental Scene**

- **Audio Elements**: 2 Background Environmental + 1 Chatter
- **Duration**: 8 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Identify all environmental sounds present
  - Focus on chatter when requested
  - Notice changes in any environmental element
- **Voice Agent Guidance**: "Listen to the conversation in the background" / "Focus on the [specific environmental sound]" / "What changed in the environment?"

**Stage 7: Music + Speech Integration**

- **Audio Elements**: 1 Vocal Music + 1 Conversation
- **Duration**: 9 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Track conversation content despite music
  - Focus on music when requested
  - Switch between music and conversation smoothly
- **Voice Agent Guidance**: "Focus on what they're discussing" / "Now listen to the song" / "Can you follow the conversation while the music plays?"

**Stage 8: Layered Music Analysis**

- **Audio Elements**: 1 Complex Instrumental Music + 1 Individual Speaker
- **Duration**: 9 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Identify multiple instruments in music
  - Follow speaker content simultaneously
  - Focus on specific musical elements when requested
- **Voice Agent Guidance**: "Focus on the [instrument]" / "What is the speaker explaining?" / "Can you hear the [specific instrument]?"

### Advanced Control Phase (stages 9-12)

**Stage 9: Quadruple Stream Challenge**

- **Audio Elements**: 2 Conversations + 1 Instrumental Music + 1 Background Environmental
- **Duration**: 9 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Maintain awareness of all four streams
  - Switch focus rapidly between any streams
  - Answer questions about any stream's content
- **Voice Agent Guidance**: "Focus on the first conversation" / "Now listen to the music" / "What's happening in the background?"

**Stage 10: Vocal Complexity**

- **Audio Elements**: 1 Vocal Music + 2 Individual Speakers + 1 Background Environmental
- **Duration**: 10 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Track both speakers despite musical vocals
  - Focus on song lyrics when requested
  - Maintain environmental awareness
- **Voice Agent Guidance**: "Listen to the song lyrics" / "Focus on what the first person is saying" / "Can you follow both speakers?"

**Stage 11: Maximum Realistic Complexity**

- **Audio Elements**: 2 Conversations + 1 Vocal Music + 2 Background Environmental
- **Duration**: 10 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Process five simultaneous audio streams
  - Rapidly switch focus between any elements
  - Maintain performance under maximum load
- **Voice Agent Guidance**: "Focus on the conversation on your left" / "Listen to what's happening outside" / "Can you hear what the song is about?"

**Stage 12: Dynamic Mastery**

- **Audio Elements**: All categories, elements fade in/out unpredictably
- **Duration**: 10 minutes, timeout at 10 minutes
- **Success Criteria**:
  - Adapt to changing audio complexity
  - Notice when elements appear/disappear
  - Maintain focus despite dynamic changes
- **Voice Agent Guidance**: "Something new just started - what is it?" / "Focus on what just became louder" / "What disappeared from the mix?"
