let lessonData = null;

/**
 * SlideValidator - ISS-079 FIX: Validates slide data and provides user feedback
 * Checks for required v1.3 fields and logs validation errors
 */
class SlideValidator {
  constructor() {
    this.validationErrors = [];
  }

  validateSlide(slide, slideIndex) {
    this.validationErrors = [];
    const sectionType = slide.section_type || slide.slide_type || 'content';
    const specVersion = lessonData?.spec_version || '';
    const isV13 = specVersion.startsWith('v1.3');

    if (!slide.section_id && !slide.id) {
      this.addError(`Slide ${slideIndex}: Missing section_id`);
    }

    if (!slide.title) {
      this.addWarning(`Slide ${slideIndex}: Missing title`);
    }

    const narration = slide.narration || {};
    const segments = narration.segments || slide.narration_segments || [];
    
    if (segments.length === 0 && !['recap'].includes(sectionType)) {
      this.addWarning(`Slide ${slideIndex}: No narration segments`);
    }

    if (isV13 && sectionType !== 'recap') {
      let missingDirectives = 0;
      for (let i = 0; i < segments.length; i++) {
        if (!segments[i].display_directives) {
          missingDirectives++;
        }
      }
      if (missingDirectives > 0 && segments.length > 0) {
        this.addError(`Slide ${slideIndex}: ${missingDirectives}/${segments.length} segments missing display_directives (v1.3 REQUIRED)`);
      }
    }

    if (sectionType === 'content' || sectionType === 'example') {
      const hasVisualContent = slide.visual_content && (
        slide.visual_content.bullet_points?.length > 0 ||
        slide.visual_content.formula
      );
      
      const hasSegmentVisualContent = segments.some(seg => 
        seg.visual_content && (
          seg.visual_content.bullet_points?.length > 0 ||
          seg.visual_content.formula
        )
      );
      
      if (!hasVisualContent && !hasSegmentVisualContent) {
        this.addWarning(`Slide ${slideIndex}: No visual_content - text display may fall back to narration`);
      }
    }

    return this.validationErrors.length === 0;
  }

  addError(message) {
    this.validationErrors.push({ level: 'error', message });
    console.error(`[SlideValidator] ERROR: ${message}`);
  }

  addWarning(message) {
    this.validationErrors.push({ level: 'warning', message });
    console.warn(`[SlideValidator] WARNING: ${message}`);
  }

  showValidationOverlay(slideIndex) {
    const errors = this.validationErrors.filter(e => e.level === 'error');
    if (errors.length === 0) return;

    let overlay = document.getElementById('validation-error-overlay');
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'validation-error-overlay';
      overlay.style.cssText = `
        position: absolute;
        top: 10px;
        right: 10px;
        background: rgba(200, 50, 50, 0.9);
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        font-size: 12px;
        max-width: 300px;
        z-index: 1000;
        cursor: pointer;
      `;
      overlay.onclick = () => overlay.style.display = 'none';
      document.getElementById('stage').appendChild(overlay);
    }

    overlay.innerHTML = `
      <strong>Slide ${slideIndex + 1} Validation Issues</strong><br>
      ${errors.map(e => `• ${e.message}`).join('<br>')}
      <br><small>(click to dismiss)</small>
    `;
    overlay.style.display = 'block';

    setTimeout(() => {
      if (overlay) overlay.style.display = 'none';
    }, 10000);
  }

  hideValidationOverlay() {
    const overlay = document.getElementById('validation-error-overlay');
    if (overlay) overlay.style.display = 'none';
  }
}

const slideValidator = new SlideValidator();

/**
 * LayerController - v1.3 display_directives handler
 * Controls text_layer, visual_layer, avatar_layer visibility
 * Enforces: text must hide BEFORE visuals appear (mutual exclusion)
 */
class LayerController {
  constructor() {
    this.currentTextState = 'hide';
    this.currentVisualState = 'hide';
    this.currentAvatarState = 'show';
    this.lastSegmentIndex = -1;
    this.pendingDirectives = null;
    this.videoReadyHandler = null;
  }

  /**
   * Check if inline video is ready to play
   */
  isVideoReady() {
    const inlineVideo = document.getElementById('inline-video');
    const videoBox = document.getElementById('video-box');
    if (!inlineVideo) return false;
    return inlineVideo.readyState >= 3 || (videoBox && videoBox.classList.contains('video-ready'));
  }

  /**
   * Apply display_directives for a narration segment
   * ISS-062 FIX: Waits for video ready before hiding text layer
   * @param {Object} segment - narration_segment with display_directives
   * @param {string} sectionType - section type (intro, content, example, etc.)
   * @param {number} segmentIndex - current segment index
   */
  applyDirectives(segment, sectionType, segmentIndex) {
    if (!segment || !segment.display_directives) {
      return;
    }
    
    if (segmentIndex === this.lastSegmentIndex) {
      return;
    }
    this.lastSegmentIndex = segmentIndex;

    const directives = segment.display_directives;
    const textLayer = directives.text_layer || 'hide';
    const visualLayer = directives.visual_layer || 'hide';
    const avatarLayer = directives.avatar_layer || 'show';

    if (textLayer === 'show' && visualLayer === 'show') {
      console.error(`[v1.3 VIOLATION] Segment ${segmentIndex}: text_layer=show + visual_layer=show violates mutual exclusion`);
    }

    if (this.videoReadyHandler) {
      const inlineVideo = document.getElementById('inline-video');
      if (inlineVideo) {
        inlineVideo.removeEventListener('canplay', this.videoReadyHandler);
      }
      this.videoReadyHandler = null;
    }

    const needsVideoGating = (textLayer === 'hide' || textLayer === 'swap') && 
                              (visualLayer === 'show' || visualLayer === 'replace') &&
                              !this.isVideoReady();

    if (needsVideoGating) {
      console.log(`[LayerController] Segment ${segmentIndex}: Waiting for video ready before hiding text...`);
      this.pendingDirectives = { textLayer, visualLayer, avatarLayer, sectionType, segmentIndex };
      
      const inlineVideo = document.getElementById('inline-video');
      if (inlineVideo) {
        this.videoReadyHandler = () => {
          console.log(`[LayerController] Video ready! Applying pending directives for segment ${segmentIndex}`);
          this.applyDirectivesImmediate(this.pendingDirectives);
          this.pendingDirectives = null;
          this.videoReadyHandler = null;
        };
        inlineVideo.addEventListener('canplay', this.videoReadyHandler, { once: true });
        
        setTimeout(() => {
          if (this.pendingDirectives && this.pendingDirectives.segmentIndex === segmentIndex) {
            console.log(`[LayerController] Video timeout - applying directives anyway for segment ${segmentIndex}`);
            this.applyDirectivesImmediate(this.pendingDirectives);
            this.pendingDirectives = null;
          }
        }, 2000);
      }
      
      this.applyAvatarDirectives(avatarLayer, sectionType);
      return;
    }

    this.applyDirectivesImmediate({ textLayer, visualLayer, avatarLayer, sectionType, segmentIndex });
  }

  /**
   * Apply directives immediately (internal helper)
   */
  applyDirectivesImmediate({ textLayer, visualLayer, avatarLayer, sectionType, segmentIndex }) {
    const stage = document.getElementById('stage');
    const segmentsList = document.getElementById('segments-list');
    const videoBox = document.getElementById('video-box');

    this.currentTextState = textLayer;
    this.currentVisualState = visualLayer;
    this.currentAvatarState = avatarLayer;

    stage.classList.remove('video-swap', 'video-focus');
    if (segmentsList) segmentsList.style.opacity = '';

    if (textLayer === 'show') {
      stage.classList.add('text-visible');
      if (segmentsList) segmentsList.style.opacity = '1';
    } else if (textLayer === 'hide') {
      stage.classList.remove('text-visible');
      if (segmentsList) segmentsList.style.opacity = '0';
      if (stage.classList.contains('mode-content-video')) {
        stage.classList.add('video-focus');
      }
    } else if (textLayer === 'swap') {
      stage.classList.add('video-swap');
      if (segmentsList) segmentsList.style.opacity = '0.3';
    }

    if (visualLayer === 'show' || visualLayer === 'replace') {
      if (videoBox) videoBox.classList.add('video-ready');
    } else if (visualLayer === 'hide') {
      if (videoBox) videoBox.classList.remove('video-ready');
    }

    this.applyAvatarDirectives(avatarLayer, sectionType);

    console.log(`[LayerController] Segment ${segmentIndex}: text=${textLayer}, visual=${visualLayer}, avatar=${avatarLayer}`);
  }

  /**
   * Apply avatar layer directives (extracted for reuse)
   * NOTE: Avatar is ALWAYS visible per REQ-004. 'hide' is no longer valid.
   * gesture_only = avatar visible with gestures (no lip-sync), still shown at reduced opacity
   */
  applyAvatarDirectives(avatarLayer, sectionType) {
    const avatarCanvas = document.getElementById('avatar-canvas');

    if (avatarCanvas) {
      avatarCanvas.style.opacity = '';
      avatarCanvas.style.transform = '';
    }

    if (avatarLayer === 'show') {
      if (avatarCanvas) avatarCanvas.style.opacity = '1';
    } else if (avatarLayer === 'gesture_only') {
      if (avatarCanvas) {
        avatarCanvas.style.opacity = '0.85';
        avatarCanvas.style.transform = 'scale(0.9)';
      }
    } else {
      if (avatarCanvas) avatarCanvas.style.opacity = '1';
    }
  }

  /**
   * Reset layer states for new slide
   */
  reset() {
    this.currentTextState = 'hide';
    this.currentVisualState = 'hide';
    this.currentAvatarState = 'show';
    this.lastSegmentIndex = -1;
    
    const avatarCanvas = document.getElementById('avatar-canvas');
    if (avatarCanvas) {
      avatarCanvas.style.opacity = '1';
      avatarCanvas.style.transform = '';
    }
  }

  /**
   * Apply section-level avatar rules (v1.3)
   * NOTE: Avatar is ALWAYS visible per REQ-004 and REQ-012.
   * The only variations are position and width_percent.
   * 
   * Avatar layout can be found in multiple locations:
   * - section.avatar_layout (from MemoryAgent/RecapAgent)
   * - section.layout?.avatar_layout (legacy)
   * - section.avatar_width_percent / section.avatar_position (from SectionPlanner)
   */
  applySectionAvatarRules(sectionType, section) {
    const avatarCanvas = document.getElementById('avatar-canvas');
    if (!avatarCanvas) return;

    avatarCanvas.style.opacity = '1';

    // ISS-165 FIX: ALWAYS use hardcoded avatar matrix - IGNORE LLM-provided values
    // This prevents LLM from overriding with small/medium/35%/52% etc.
    let widthPercent = 55;
    let position = 'right';

    if (sectionType === 'intro') {
      widthPercent = 80;
      position = 'center';
    }

    this.applyAvatarLayout(avatarCanvas, position, widthPercent);
  }

  /**
   * Get default avatar width by section type
   * ISS-165 FIX: FINAL AVATAR MATRIX - Player IGNORES LLM width values
   * Intro = 80% center (large, full-focus)
   * ALL others = 55% right (content sections have 45% left for text/video)
   */
  getDefaultAvatarWidth(sectionType) {
    if (sectionType === 'intro') {
      return 80;
    }
    return 55;
  }

  /**
   * Get default avatar position by section type
   */
  getDefaultAvatarPosition(sectionType) {
    switch (sectionType) {
      case 'intro': return 'center';
      default: return 'right';
    }
  }

  /**
   * Apply avatar layout (position and width) - REQ-030/031
   */
  applyAvatarLayout(avatarCanvas, position, widthPercent) {
    avatarCanvas.style.position = 'absolute';
    avatarCanvas.style.width = `${widthPercent}%`;
    avatarCanvas.style.maxWidth = '600px';
    avatarCanvas.style.height = 'auto';

    avatarCanvas.style.left = '';
    avatarCanvas.style.right = '';
    avatarCanvas.style.transform = '';

    if (position === 'center') {
      avatarCanvas.style.left = '50%';
      avatarCanvas.style.transform = 'translateX(-50%)';
      avatarCanvas.style.bottom = '0';
    } else if (position === 'right') {
      avatarCanvas.style.right = '10px';
      avatarCanvas.style.bottom = '0';
    } else if (position === 'left') {
      avatarCanvas.style.left = '10px';
      avatarCanvas.style.bottom = '0';
    }

    console.log(`[LayerController] Avatar layout: position=${position}, width=${widthPercent}%`);
  }
}

const layerController = new LayerController();

/**
 * VideoBufferManager - Preload-based smooth video transitions (ISS-070)
 * Preloads next video in hidden element, copies to primary when ready
 * Does NOT swap DOM elements - keeps inlineVideo reference stable
 */
class VideoBufferManager {
  constructor() {
    this.preload = null;
    this.nextVideoPath = null;
    this.preloadReady = false;
    this.pendingSwitch = null;
  }

  init() {
    this.preload = document.getElementById('inline-video-preload');
    if (this.preload) {
      this.preload.addEventListener('canplaythrough', () => {
        this.preloadReady = true;
        console.log(`[VideoBuffer] Preloaded ready: ${this.nextVideoPath}`);
        if (this.pendingSwitch && this.pendingSwitch.path === this.nextVideoPath) {
          this.executePendingSwitch();
        }
      });
    }
  }

  preloadVideo(videoPath) {
    if (!this.preload || !videoPath) return;
    if (this.nextVideoPath === videoPath) return;
    
    console.log(`[VideoBuffer] Preloading: ${videoPath}`);
    this.nextVideoPath = videoPath;
    this.preloadReady = false;
    this.preload.src = videoPath;
    this.preload.load();
  }

  switchTo(inlineVideo, videoPath, playbackRate = 1.0) {
    if (!inlineVideo || !videoPath) return;
    
    // ISS-088 FIX: Clear video-ready class immediately so LayerController knows video is not ready yet
    const videoBox = document.getElementById('video-box');
    if (videoBox) {
      videoBox.classList.remove('video-ready');
    }
    
    // Setup canplay listener to mark video ready when new video is actually playable
    const markVideoReady = () => {
      if (videoBox) videoBox.classList.add('video-ready');
      inlineVideo.removeEventListener('canplay', markVideoReady);
    };
    inlineVideo.addEventListener('canplay', markVideoReady);
    
    if (this.preload && this.nextVideoPath === videoPath && this.preloadReady) {
      console.log(`[VideoBuffer] Instant switch to preloaded: ${videoPath}`);
      inlineVideo.src = videoPath;
      inlineVideo.playbackRate = playbackRate;
      inlineVideo.play().catch(e => console.log("Video play fail", e));
      this.preloadReady = false;
      this.nextVideoPath = null;
    } else {
      this.pendingSwitch = { video: inlineVideo, path: videoPath, rate: playbackRate };
      this.preloadVideo(videoPath);
      
      setTimeout(() => {
        if (this.pendingSwitch && this.pendingSwitch.path === videoPath) {
          console.log(`[VideoBuffer] Fallback load: ${videoPath}`);
          inlineVideo.src = videoPath;
          inlineVideo.load();
          inlineVideo.playbackRate = playbackRate;
          inlineVideo.play().catch(e => console.log("Video play fail", e));
          this.pendingSwitch = null;
        }
      }, 150);
    }
  }

  executePendingSwitch() {
    if (!this.pendingSwitch) return;
    const { video, path, rate } = this.pendingSwitch;
    console.log(`[VideoBuffer] Executing pending switch: ${path}`);
    video.src = path;
    video.playbackRate = rate;
    video.play().catch(e => console.log("Video play fail", e));
    this.pendingSwitch = null;
  }

  preloadNext(currentIndex, videoPaths) {
    const nextIndex = currentIndex + 1;
    if (nextIndex < videoPaths.length) {
      this.preloadVideo(videoPaths[nextIndex]);
    }
  }
}

const videoBufferManager = new VideoBufferManager();

function getBasePath() {
  const path = window.location.pathname;
  const params = new URLSearchParams(window.location.search);
  const jobParam = params.get('job');
  
  if (jobParam) {
    return `/player/jobs/${jobParam}/`;
  }
  
  const newJobMatch = path.match(/\/jobs\/([^\/]+)\//);
  if (newJobMatch) {
    return `/player/jobs/${newJobMatch[1]}/`;
  }
  
  const legacyJobMatch = path.match(/\/player\/jobs\/([^\/]+)\//);
  if (legacyJobMatch) {
    return `/player/jobs/${legacyJobMatch[1]}/`;
  }
  
  return '/player/assets/';
}

const BASE_PATH = getBasePath();
console.log(`Player BASE_PATH: ${BASE_PATH}`);
// ISS-060 FIX: Avatar is in shared assets folder, not job folder
const AVATAR_URL = "/player/assets/avatar_placeholder.mp4";

let currentSlideIndex = 0;
let isPlaying = false;
let currentBeatIndex = 0;
let beatVideoPaths = [];

const videoDetectionCache = {};

async function detectBeatVideos(sectionId) {
  if (videoDetectionCache[sectionId]) {
    return videoDetectionCache[sectionId];
  }
  
  const beats = [];
  for (let i = 0; i < 20; i++) {
    const path = BASE_PATH + `videos/topic_${sectionId}_beat_${i}.mp4`;
    try {
      const resp = await fetch(path, { method: 'HEAD' });
      if (resp.ok) {
        beats.push(path);
      } else {
        break;
      }
    } catch (e) {
      break;
    }
  }
  videoDetectionCache[sectionId] = beats;
  return beats;
}

async function detectVideosForSlide(slide) {
  const sectionId = slide.section_id || slide.id;
  if (!sectionId || slide._videoDetected) return;
  
  try {
    // ISS-061 FIX: Prefer video_path metadata from presentation if available
    if (slide.video_path) {
      // Use metadata path directly (already set by pipeline)
      slide.content_video_path = slide.video_path.startsWith('/') ? slide.video_path : BASE_PATH + slide.video_path;
      slide.has_content_video = true;
      console.log(`Section ${sectionId}: Using metadata video_path: ${slide.content_video_path}`);
      slide._videoDetected = true;
      return;
    }
    
    // ISS-134 FIX: Only check for videos if renderer indicates video content
    const renderer = slide.renderer || 'none';
    const sectionType = slide.section_type || slide.slide_type || 'content';
    
    // Skip video detection for text-only sections (intro, summary, memory, quiz with no video renderer)
    if (renderer === 'none' && ['intro', 'summary', 'memory', 'quiz'].includes(sectionType)) {
      slide._videoDetected = true;
      slide.has_content_video = false;
      return;
    }
    
    // Only check for videos if renderer is manim, video, or wan_video
    if (!['manim', 'video', 'wan_video', 'remotion'].includes(renderer)) {
      slide._videoDetected = true;
      slide.has_content_video = false;
      return;
    }
    
    // Fallback: Check for beat videos (silently, no console errors)
    const beats = await detectBeatVideos(sectionId);
    if (beats.length > 0) {
      slide.beat_videos = beats;
      slide.content_video_path = beats[0];
      slide.has_content_video = true;
      console.log(`Section ${sectionId}: Found ${beats.length} beat videos`);
    } else {
      // Fallback: Check for single topic video
      const singleVideoPath = `${BASE_PATH}videos/topic_${sectionId}.mp4`;
      try {
        const resp = await fetch(singleVideoPath, { method: 'HEAD' });
        if (resp.ok) {
          slide.content_video_path = singleVideoPath;
          slide.has_content_video = true;
          console.log(`Section ${sectionId}: Found single video at ${singleVideoPath}`);
        } else {
          // Video expected but not found - log warning but don't spam console
          console.warn(`Section ${sectionId}: Expected video not found (renderer=${renderer})`);
          slide.has_content_video = false;
        }
      } catch (fetchErr) {
        slide.has_content_video = false;
      }
    }
    slide._videoDetected = true;
  } catch (e) {
    console.log(`Video detection error for ${sectionId}:`, e);
    slide._videoDetected = true;
    slide.has_content_video = false;
  }
}

const stage = document.getElementById('stage');
const contentBox = document.getElementById('content-box');
const avatarCanvas = document.getElementById('avatar-canvas');
const video = document.getElementById('raw-avatar-video');
const audio = document.getElementById('main-audio');
const ctx = avatarCanvas.getContext('2d', { willReadFrequently: true });

let currentMedia = audio;
let currentVisibleImage = null;

function updateSlideImages(slide, currentTime) {
  const imageLayer = document.getElementById('image-display-layer');
  if (!imageLayer) return;
  
  const sectionType = slide.section_type || slide.slide_type || 'content';
  if (sectionType === 'intro' || sectionType === 'memory' || sectionType === 'recap' || sectionType === 'summary' || sectionType === 'quiz') {
    imageLayer.innerHTML = '';
    currentVisibleImage = null;
    return;
  }
  
  if (!slide.images || slide.images.length === 0) {
    if (!slide.visual_beats) return;
    const hasImages = slide.visual_beats.some(vb => vb.image_ref || vb.image_filename);
    if (!hasImages) return;
  }
  
  let imagesToShow = [];
  
  if (slide.images && slide.images.length > 0) {
    slide.images.forEach((img, i) => {
      const appearTime = img.appear_time || (slide.timed_segments?.[i]?.start_time) || 0;
      if (currentTime >= appearTime) {
        imagesToShow.push({
          src: `${BASE_PATH}images/${img.filename}`,
          alt: img.alt_text || `Image ${i + 1}`,
          id: img.image_ref || `img-${i}`
        });
      }
    });
  }
  
  if (slide.visual_beats) {
    slide.visual_beats.forEach((vb, i) => {
      if (vb.image_ref && vb.image_filename) {
        const segStart = slide.timed_segments?.[i]?.start_time || 0;
        const appearOffset = vb.image_appear_time || 0;
        const appearTime = segStart + appearOffset;
        
        if (currentTime >= appearTime) {
          imagesToShow.push({
            src: `${BASE_PATH}images/${vb.image_filename}`,
            alt: vb.image_ref,
            id: vb.image_ref
          });
        }
      }
    });
  }
  
  const latestImage = imagesToShow.length > 0 ? imagesToShow[imagesToShow.length - 1] : null;
  
  if (latestImage && latestImage.id !== currentVisibleImage) {
    currentVisibleImage = latestImage.id;
    
    const existingImgs = imageLayer.querySelectorAll('.slide-image');
    existingImgs.forEach(img => img.classList.remove('visible'));
    
    let imgEl = imageLayer.querySelector(`img[data-id="${latestImage.id}"]`);
    if (!imgEl) {
      imgEl = document.createElement('img');
      imgEl.className = 'slide-image';
      imgEl.src = latestImage.src;
      imgEl.alt = latestImage.alt;
      imgEl.dataset.id = latestImage.id;
      imageLayer.appendChild(imgEl);
    }
    
    setTimeout(() => imgEl.classList.add('visible'), 50);
  } else if (!latestImage && currentVisibleImage) {
    currentVisibleImage = null;
    const existingImgs = imageLayer.querySelectorAll('.slide-image');
    existingImgs.forEach(img => img.classList.remove('visible'));
  }
}

function setupContentOverflowHandler() {
  const contentWrapper = document.getElementById('content-wrapper');
  if (!contentBox || !contentWrapper) return;
  
  const resizeObserver = new ResizeObserver(() => {
    adjustContentScale();
  });
  
  resizeObserver.observe(contentBox);
  
  const mutationObserver = new MutationObserver(() => {
    setTimeout(adjustContentScale, 100);
  });
  mutationObserver.observe(contentBox, { childList: true, subtree: true });
}

function adjustContentScale() {
  const contentWrapper = document.getElementById('content-wrapper');
  const segmentsList = document.getElementById('segments-list');
  if (!contentBox || !contentWrapper || !segmentsList) return;
  
  const maxHeight = contentBox.clientHeight - 80;
  const currentHeight = segmentsList.scrollHeight;
  
  if (currentHeight > maxHeight && maxHeight > 0) {
    const scale = Math.max(0.65, maxHeight / currentHeight);
    segmentsList.style.transform = `scale(${scale})`;
    segmentsList.style.transformOrigin = 'top left';
    segmentsList.style.width = `${100 / scale}%`;
  } else {
    segmentsList.style.transform = '';
    segmentsList.style.width = '';
  }
}

if (AVATAR_URL) {
  video.src = AVATAR_URL;
  video.load();
}

function updateVisuals() {
  const aScale = document.getElementById('av-scale').value;
  const aX = document.getElementById('av-x').value;
  const cScale = document.getElementById('con-scale').value;

  avatarCanvas.style.transform = `translateX(${aX}px) scale(${aScale})`;
  contentBox.style.transform = `scale(${cScale})`;
  updateDevStats();
}

function updateDevStats() {
  const overlay = document.getElementById('dev-stats-overlay');
  if (!overlay || !overlay.classList.contains('visible')) return;
  
  const avatar = document.getElementById('avatar-canvas');
  const content = document.getElementById('content-box');
  const videoBox = document.getElementById('video-box');
  const stageEl = document.getElementById('stage');
  
  const modeClasses = ['mode-intro', 'mode-center', 'mode-side', 'mode-khan', 'mode-content-video', 'mode-image'];
  let currentMode = 'unknown';
  for (const mode of modeClasses) {
    if (stageEl.classList.contains(mode)) {
      currentMode = mode.replace('mode-', '');
      break;
    }
  }
  
  const slide = lessonData?.slides?.[currentSlideIndex];
  const sectionType = slide?.section_type || slide?.slide_type || '-';
  
  document.getElementById('stat-mode').textContent = currentMode;
  document.getElementById('stat-section').textContent = sectionType;
  
  if (avatar) {
    const rect = avatar.getBoundingClientRect();
    const stageRect = stageEl.getBoundingClientRect();
    const relRight = Math.round(stageRect.right - rect.right);
    const relBottom = Math.round(stageRect.bottom - rect.bottom);
    document.getElementById('stat-avatar-pos').textContent = `R:${relRight}px B:${relBottom}px`;
    document.getElementById('stat-avatar-size').textContent = `${Math.round(rect.width)}x${Math.round(rect.height)}`;
    const aspect = rect.height > 0 ? (rect.width / rect.height).toFixed(2) : '-';
    document.getElementById('stat-avatar-aspect').textContent = aspect;
  }
  
  if (content) {
    const rect = content.getBoundingClientRect();
    const stageRect = stageEl.getBoundingClientRect();
    const relLeft = Math.round(rect.left - stageRect.left);
    const relTop = Math.round(rect.top - stageRect.top);
    document.getElementById('stat-content-pos').textContent = `L:${relLeft}px T:${relTop}px`;
    document.getElementById('stat-content-size').textContent = `${Math.round(rect.width)}x${Math.round(rect.height)}`;
  }
  
  if (videoBox) {
    const rect = videoBox.getBoundingClientRect();
    const isVisible = stageEl.classList.contains('mode-content-video') && rect.width > 0;
    document.getElementById('stat-video-size').textContent = `${Math.round(rect.width)}x${Math.round(rect.height)}`;
    document.getElementById('stat-video-visible').textContent = isVisible ? 'Yes' : 'No';
  }
}

setInterval(() => {
  if (document.getElementById('dev-stats-overlay')?.classList.contains('visible')) {
    updateDevStats();
  }
}, 500);

function renderAvatar() {
  if ((!video.paused && !video.ended) || video.readyState >= 2) {
    if (canvasSizeMismatch()) syncCanvasSize();
    if (avatarCanvas.width === 0 || avatarCanvas.height === 0) {
      requestAnimationFrame(renderAvatar);
      return;
    }

    ctx.drawImage(video, 0, 0, avatarCanvas.width, avatarCanvas.height);
    const frame = ctx.getImageData(0, 0, avatarCanvas.width, avatarCanvas.height);
    const data = frame.data;
    const thresh = parseInt(document.getElementById('av-green').value);

    for (let i = 0; i < data.length; i += 4) {
      const r = data[i], g = data[i + 1], b = data[i + 2];
      if (g > thresh && g > r * 1.3 && g > b * 1.3) data[i + 3] = 0;
    }
    ctx.putImageData(frame, 0, 0);
  }
  requestAnimationFrame(renderAvatar);
}

function canvasSizeMismatch() { return avatarCanvas.width !== video.videoWidth; }
function syncCanvasSize() { avatarCanvas.width = video.videoWidth; avatarCanvas.height = video.videoHeight; }

video.addEventListener('play', renderAvatar);
video.addEventListener('loadeddata', renderAvatar);

function loadSlide(index) {
  if (!lessonData || index >= lessonData.slides.length || index < 0) return;

  video.pause();
  audio.pause();

  layerController.reset();
  slideValidator.hideValidationOverlay();

  currentSlideIndex = index;
  currentBeatIndex = 0;
  const slide = lessonData.slides[index];
  
  slideValidator.validateSlide(slide, index);
  if (slideValidator.validationErrors.filter(e => e.level === 'error').length > 0) {
    slideValidator.showValidationOverlay(index);
  }
  
  const sectionType = slide.section_type || slide.slide_type || 'content';
  layerController.applySectionAvatarRules(sectionType, slide);

  document.querySelectorAll('.slide-thumb').forEach((el, i) => {
    el.classList.toggle('active', i === index);
  });

  const slideTitle = slide.title || 'Untitled';
  if (document.getElementById('slide-title')) document.getElementById('slide-title').innerText = slideTitle;

  const list = document.getElementById('segments-list');
  list.innerHTML = '';

  const imgContainer = document.getElementById('slide-image-container');
  const bgImg = document.getElementById('bg-image-layer');
  const sceneLabel = document.getElementById('scene-label');

  if (sectionType === 'example') {
    document.getElementById('content-box').classList.add('example-section');
  } else {
    document.getElementById('content-box').classList.remove('example-section');
  }

  if (sectionType === 'quiz' && slide.quiz) {
    const quiz = slide.quiz;
    const container = document.createElement('div');
    container.className = 'quiz-container';
    
    const questionDiv = document.createElement('div');
    questionDiv.className = 'quiz-question';
    questionDiv.innerHTML = `<span class="quiz-q-mark">Q:</span> ${quiz.question?.text || quiz.question || ''}`;
    container.appendChild(questionDiv);
    
    const choicesDiv = document.createElement('div');
    choicesDiv.className = 'quiz-choices';
    (quiz.choices || []).forEach((choice, i) => {
      const choiceEl = document.createElement('div');
      choiceEl.className = 'quiz-choice';
      choiceEl.id = `choice-${choice.id || i}`;
      choiceEl.dataset.choiceId = choice.id || String.fromCharCode(65 + i);
      choiceEl.innerHTML = `<span class="choice-letter">${choice.id || String.fromCharCode(65 + i)}</span> ${choice.text}`;
      choicesDiv.appendChild(choiceEl);
    });
    container.appendChild(choicesDiv);
    
    if (quiz.answer_reveal && quiz.answer_reveal.reveal_steps) {
      const revealDiv = document.createElement('div');
      revealDiv.className = 'quiz-reveal-steps';
      revealDiv.id = 'quiz-reveal-container';
      quiz.answer_reveal.reveal_steps.forEach((step, i) => {
        const stepEl = document.createElement('div');
        stepEl.className = 'quiz-reveal-step';
        stepEl.id = `reveal-step-${i}`;
        stepEl.innerHTML = `<strong>${step.title || `Step ${step.step_id}`}:</strong> ${step.explanation || ''}`;
        revealDiv.appendChild(stepEl);
      });
      container.appendChild(revealDiv);
      
      slide.quizData = {
        correctChoiceId: quiz.correct_choice_id,
        revealStepCount: quiz.answer_reveal.reveal_steps.length,
        choices: quiz.choices || []
      };
    }
    
    document.querySelectorAll('.quiz-choice').forEach(ch => {
      ch.classList.remove('correct', 'incorrect', 'active');
    });
    
    list.appendChild(container);
    document.getElementById('content-box').style.width = '75%';
    
    const quizNarrationSegs = slide.narration?.segments || slide.narration_segments;
    if (quizNarrationSegs && quizNarrationSegs.length > 0) {
      let cumulativeTime = 0;
      slide.timed_segments = quizNarrationSegs.map(seg => {
        const duration = seg.duration_seconds || seg.duration || 5;
        const start = cumulativeTime;
        cumulativeTime += duration;
        return { start_time: start, end_time: cumulativeTime, step_id: seg.id };
      });
    }
  } else if (sectionType === 'memory' && ((slide.visual_beats && slide.visual_beats.length > 0) || (slide.flashcards && slide.flashcards.length > 0))) {
    const memoryCards = (slide.visual_beats && slide.visual_beats.length > 0) ? slide.visual_beats : slide.flashcards;
    const container = document.createElement('div');
    container.className = 'flashcard-container';
    memoryCards.forEach((fc, i) => {
      const card = document.createElement('div');
      card.className = 'flashcard';
      card.id = `seg-${i}`;
      if (fc.letter && fc.mnemonic) {
        card.innerHTML = `
          <div class="fc-letter">${fc.letter}</div>
          <div class="fc-title">${fc.title || ''}</div>
          <div class="fc-mnemonic">${fc.mnemonic || ''}</div>
        `;
      } else if (fc.visual_beat_type === 'flashcard') {
        // ISS-063 FIX: Parse flashcard description to extract question and answer
        let question = fc.concept_title || fc.title || '';
        let answer = fc.description || '';
        
        // Parse description pattern: "Flashcard front shows 'X'. Flips to reveal 'Y'."
        const descMatch = (fc.description || '').match(/front shows ['"]([^'"]+)['"]\. Flips to reveal ['"]([^'"]+)['"]/i);
        if (descMatch) {
          question = descMatch[1];
          answer = descMatch[2];
        }
        
        card.className = 'flashcard flip-card';
        card.innerHTML = `
          <div class="flip-card-inner">
            <div class="flip-card-front">
              <div class="fc-label">Question</div>
              <div class="fc-question">${question}</div>
            </div>
            <div class="flip-card-back">
              <div class="fc-label">Answer</div>
              <div class="fc-answer">${answer}</div>
            </div>
          </div>
        `;
        card.onclick = () => card.classList.toggle('flipped');
      } else {
        card.innerHTML = `
          <div class="fc-question">${fc.question || fc.title || fc.concept_title || ''}</div>
          <div class="fc-answer">${fc.answer || fc.description || ''}</div>
        `;
      }
      container.appendChild(card);
    });
    list.appendChild(container);
    document.getElementById('content-box').style.width = '70%';

    const memoryNarrationSegs = slide.narration?.segments || slide.narration_segments;
    if (memoryNarrationSegs && memoryNarrationSegs.length > 0 && !slide.timed_segments) {
      let cumulativeTime = 0;
      slide.timed_segments = memoryNarrationSegs.map((seg, i) => {
        const duration = seg.duration_seconds || seg.duration || 5;
        const start = cumulativeTime;
        cumulativeTime += duration;
        return { start_time: start, end_time: cumulativeTime };
      });
    } else if (slide.audio_duration && !slide.timed_segments) {
      const durationPerItem = slide.audio_duration / memoryCards.length;
      slide.timed_segments = memoryCards.map((_, i) => ({
        start_time: i * durationPerItem,
        end_time: (i + 1) * durationPerItem
      }));
    }
  } else if (slide.visual_content && slide.visual_content.flashcards) {
    const container = document.createElement('div');
    container.className = 'flashcard-container';
    slide.visual_content.flashcards.forEach((fc, i) => {
      const card = document.createElement('div');
      card.className = 'flashcard';
      card.id = `seg-${i}`;
      if (fc.letter && fc.mnemonic) {
        card.innerHTML = `
          <div class="fc-letter">${fc.letter}</div>
          <div class="fc-title">${fc.title || ''}</div>
          <div class="fc-mnemonic">${fc.mnemonic || ''}</div>
        `;
      } else {
        card.innerHTML = `<div class="fc-letter">${fc.letter || ''}</div><div class="fc-title">${fc.title || ''}</div>`;
      }
      container.appendChild(card);
    });
    list.appendChild(container);
    document.getElementById('content-box').style.width = '70%';

    if (slide.audio_duration && !slide.timed_segments) {
      const durationPerItem = slide.audio_duration / slide.visual_content.flashcards.length;
      slide.timed_segments = slide.visual_content.flashcards.map((_, i) => ({
        start_time: i * durationPerItem,
        end_time: (i + 1) * durationPerItem
      }));
    }
  } else {
    document.getElementById('content-box').style.width = '55%';

    let displayItems = [];
    const narrationSegs = slide.narration?.segments || slide.narration_segments;
    
    const specVersion = lessonData.spec_version || '';
    const legacyVersions = ['', 'v1.0', 'v1.1', 'v1.2'];
    const isLegacy = legacyVersions.includes(specVersion);
    
    // ISS-160: Handle content_type for source fidelity display
    const contentType = slide.visual_content?.content_type;
    
    if (contentType === 'paragraph' && slide.visual_content?.verbatim_text) {
      // ISS-160: Paragraph mode - display as prose text (not bullets)
      const paragraphDiv = document.createElement('div');
      paragraphDiv.className = 'segment-item paragraph-content';
      paragraphDiv.id = 'seg-0';
      paragraphDiv.innerHTML = slide.visual_content.verbatim_text;
      list.appendChild(paragraphDiv);
      displayItems = [slide.visual_content.verbatim_text];
      console.log(`[ISS-160] Slide ${slide.slide_number}: Rendering paragraph mode`);
    } else if (contentType === 'ordered_list' && slide.visual_content?.ordered_list?.length > 0) {
      // ISS-160: Ordered list mode - display with numbered markers
      slide.visual_content.ordered_list.forEach((item, i) => {
        const div = document.createElement('div');
        div.className = 'segment-item ordered-list-item';
        div.id = `seg-${i}`;
        div.innerHTML = `<span class="list-number">${i + 1}.</span> ${item}`;
        list.appendChild(div);
      });
      displayItems = slide.visual_content.ordered_list;
      console.log(`[ISS-160] Slide ${slide.slide_number}: Rendering ordered_list mode (${displayItems.length} items)`);
    } else if (contentType === 'formula' && (slide.visual_content?.formula || slide.visual_content?.formulas?.length > 0)) {
      // ISS-160: Formula mode - centered LaTeX display
      const formulas = slide.visual_content.formulas || [slide.visual_content.formula];
      formulas.forEach((formula, i) => {
        const div = document.createElement('div');
        div.className = 'segment-item formula-content';
        div.id = `seg-${i}`;
        div.innerHTML = formula;
        list.appendChild(div);
      });
      displayItems = formulas;
      console.log(`[ISS-160] Slide ${slide.slide_number}: Rendering formula mode (${displayItems.length} formulas)`);
    } else if (slide.visual_content && slide.visual_content.bullet_points && slide.visual_content.bullet_points.length > 0) {
      displayItems = slide.visual_content.bullet_points;
    } else if (isLegacy && narrationSegs && narrationSegs.length > 0) {
      displayItems = narrationSegs.map(seg => seg.text || '');
      console.warn(`[Legacy Mode] Slide ${slide.slide_number}: Using narration text as display (${specVersion || 'unversioned'} content)`);
    } else if (!isLegacy && narrationSegs && narrationSegs.length > 0) {
      const textLayerShowSegs = narrationSegs.filter(seg => 
        seg.display_directives && seg.display_directives.text_layer === 'show'
      );
      if (textLayerShowSegs.length > 0) {
        console.error(`[v1.3+ VIOLATION] Slide ${slide.slide_number}: text_layer=show segments exist but no visual_content provided.`);
        displayItems = [{ level: 1, text: '[Missing display content - visual_content required]' }];
      }
    } else if (slide.visual_beats && slide.visual_beats.length > 0) {
      displayItems = slide.visual_beats.map(vb => {
        const lt = vb.labels_and_text || '';
        const quoted = lt.match(/'([^']+)'/g);
        if (quoted && quoted.length > 0) {
          return quoted.map(q => q.replace(/'/g, '')).join(' | ');
        }
        return vb.purpose || vb.pedagogical_focus || lt || '';
      });
    } else if (slide.segments && slide.segments.length > 0) {
      displayItems = slide.segments.map(s => s.visual || s.text || '');
    }

    if (Array.isArray(displayItems) && displayItems.length > 0) {
      displayItems.forEach((item, i) => {
        const div = document.createElement('div');
        div.className = 'segment-item';
        div.id = `seg-${i}`;
        if (typeof item === 'object' && item.level) {
          div.classList.add(`bullet-level-${item.level}`);
          div.innerHTML = item.text || '';
        } else {
          div.innerHTML = typeof item === 'string' ? item : (item.visual || item.text || '');
        }
        list.appendChild(div);
      });

      const timingSource = narrationSegs || displayItems;
      if (timingSource && timingSource.length > 0) {
        let cumulativeTime = 0;
        slide.timed_segments = timingSource.map((item, i) => {
          const duration = item.duration_seconds || item.duration || 5;
          const start = cumulativeTime;
          cumulativeTime += duration;
          return {
            visual: displayItems[i] || '',
            start_time: start,
            end_time: cumulativeTime
          };
        });
      }
      
      const firstSeg = document.getElementById('seg-0');
      if (firstSeg) firstSeg.classList.add('active');
    }
  }

  const firstFlashcard = document.querySelector('.flashcard');
  if (firstFlashcard) firstFlashcard.classList.add('active');
  
  // Toggle text-visible class based on whether content-box has visible content
  const stageForText = document.getElementById('stage');
  const segmentsList = document.getElementById('segments-list');
  if (stageForText) {
    const hasSegments = segmentsList && segmentsList.children.length > 0;
    const hasFlashcards = document.querySelector('.flashcard') !== null;
    const hasQuiz = document.querySelector('.quiz-container') !== null;
    
    if (hasSegments || hasFlashcards || hasQuiz) {
      stageForText.classList.add('text-visible');
    } else {
      stageForText.classList.remove('text-visible');
    }
  }

  if (window.MathJax) MathJax.typesetPromise();

  let isHeyGen = slide.use_heygen_audio || slide.video_path;

  if (isHeyGen) {
    currentMedia = video;
    let vidSrc = slide.avatar_video_url || slide.video_path;

    if (video.src.indexOf(vidSrc) === -1) {
      video.src = vidSrc;
    }
    video.muted = false;
    video.loop = false;
    audio.src = '';
  } else {
    let audSrc = slide.audio_path || '';
    if (audSrc && !audSrc.startsWith('http') && !audSrc.startsWith('/')) {
      audSrc = audSrc.replace(/^output\/v[34]-?[^/]*\//, '');
    }

    currentMedia = audio;

    if (video.src.indexOf(AVATAR_URL) === -1) {
      video.src = AVATAR_URL;
    }
    video.muted = true;
    video.loop = true;

    audio.src = audSrc;
  }

  if (currentMedia.readyState === 0) currentMedia.load();

  if (currentMedia !== video) {
    if (video.paused) video.play().catch(e => console.log("Auto-play loop failed", e));
  }

  if (isPlaying) {
    currentMedia.play();
    if (currentMedia === audio && video.paused) video.play();
  }

  bgImg.src = '';
  bgImg.style.opacity = 0;
  if (sceneLabel) {
    sceneLabel.innerText = '';
    sceneLabel.style.opacity = 0;
  }

  if (sectionType === 'intro') {
    stage.className = 'mode-intro';
  } else if (sectionType === 'recap') {
    if (slide.has_content_video || slide.content_video_path) {
      stage.className = 'mode-side';
    } else {
      stage.className = 'mode-image';
      const scenes = (slide.visual_beats && slide.visual_beats.length > 0) ? slide.visual_beats : (slide.recap_scenes || slide.storyboard_scenes);
      if (scenes && scenes.length > 0) {
        if (scenes[0].image_url) {
          bgImg.src = scenes[0].image_url;
          bgImg.style.opacity = 1;
        }
        if (sceneLabel) {
          sceneLabel.innerText = scenes[0].concept_title || scenes[0].description || 'Scene 1';
          sceneLabel.style.opacity = 1;
        }
      }
    }
  } else if (sectionType === 'summary') {
    stage.className = 'mode-side';
    document.getElementById('content-box').style.width = '60%';
  } else if (sectionType === 'memory') {
    stage.className = 'mode-center';
    document.getElementById('content-box').style.width = '80%';
  } else {
    stage.className = 'mode-side';
    if (slide.image_id) {
      if (imgContainer) {
        imgContainer.style.display = 'block';
        imgContainer.innerHTML = `<img src="images/${slide.image_id}">`;
      }
      bgImg.src = "images/" + slide.image_id;
      bgImg.style.opacity = 0.2;
    } else {
      if (imgContainer) imgContainer.style.display = 'none';
      bgImg.src = '';
      bgImg.style.opacity = 0;
    }
  }

  updateVisuals();

  const bgVideo = document.getElementById('scene-video');
  const bgVidPath = slide.background_video;
  
  const hasBeatVideos = slide.beat_videos && slide.beat_videos.length > 0;
  const contentVidPath = hasBeatVideos ? slide.beat_videos[0] : slide.content_video_path;

  const inlineVideo = document.getElementById('inline-video');
  const videoBox = document.getElementById('video-box');
  
  const showVideoBox = (sectionType !== 'intro' && sectionType !== 'memory') || 
                       (sectionType === 'recap' && (slide.has_content_video || slide.content_video_path));

  const hasValidVideoAsset = contentVidPath && slide.has_content_video;
  
  if (showVideoBox && (hasValidVideoAsset || hasBeatVideos)) {
    stage.classList.remove('mode-khan');
    stage.classList.remove('mode-side');
    stage.classList.remove('mode-center');
    stage.classList.add('mode-content-video');
    stage.classList.remove('video-swap');
    stage.classList.remove('video-focus');
    
    const firstBeat = slide.visual_beats && slide.visual_beats[0];
    const displayMode = firstBeat?.display_mode || 'video_primary';
    
    if (hasValidVideoAsset || hasBeatVideos) {
      if (displayMode === 'video_only') {
        stage.classList.add('video-focus');
      } else if (displayMode === 'text_primary') {
        stage.classList.add('video-swap');
      }
    }
    
    console.log(`Loading video for section ${slide.id}: ${contentVidPath}, display_mode: ${displayMode}`);
    
    if (videoBox) {
      videoBox.classList.remove('video-ready');
    }
    if (inlineVideo && contentVidPath && !inlineVideo.src.includes(contentVidPath)) {
      inlineVideo.src = contentVidPath;
      inlineVideo.load();
    }
    if (inlineVideo) {
      inlineVideo.muted = true;
      inlineVideo.playbackRate = 0.7;
      inlineVideo.oncanplay = () => {
        if (videoBox) videoBox.classList.add('video-ready');
        inlineVideo.oncanplay = null;
      };
      if (inlineVideo.readyState >= 3) {
        if (videoBox) videoBox.classList.add('video-ready');
      }
      setTimeout(() => {
        if (inlineVideo.paused) {
          inlineVideo.play().catch(e => {});
        }
      }, 100);
      
      // ISS-089 FIX: Preload second recap video at slide start (before first switch)
      if (sectionType === 'recap' && slide.recap_video_paths && slide.recap_video_paths.length > 1) {
        console.log(`[ISS-089] Preloading second recap video at slide start`);
        videoBufferManager.preloadVideo(slide.recap_video_paths[1]);
      }
    }
    
    bgVideo.pause();
    bgVideo.style.opacity = 0;
  } else if (bgVidPath) {
    stage.classList.remove('mode-content-video');
    stage.classList.remove('video-swap');
    stage.classList.add('mode-khan');
    if (inlineVideo) inlineVideo.pause();

    if (bgVideo.src.indexOf(bgVidPath) === -1) {
      bgVideo.src = bgVidPath;
      bgVideo.load();
    }
    bgVideo.play().catch(e => console.log("BG Video Play Fail", e));
  } else {
    stage.classList.remove('mode-khan');
    stage.classList.remove('mode-content-video');
    stage.classList.remove('video-swap');
    bgVideo.pause();
    bgVideo.style.opacity = 0;
    if (inlineVideo) inlineVideo.pause();
  }

  adjustContentScale();
  renderAvatar();
  
  if (!slide._videoDetected) {
    detectVideosForSlide(slide).then(() => {
      if (currentSlideIndex === index && slide.has_content_video) {
        loadSlide(index);
      }
    });
  }
}

function handleTimeUpdate(e) {
  if (e.target !== currentMedia) return;

  const t = currentMedia.currentTime;
  const duration = currentMedia.duration;
  const slide = lessonData.slides[currentSlideIndex];

  if (duration && !isNaN(duration)) {
    document.getElementById('timeline-fill').style.width = (t / duration * 100) + '%';
  }
  document.getElementById('time-display').innerText = formatTime(t);

  const bgVideo = document.getElementById('scene-video');
  if (stage.classList.contains('mode-khan') && bgVideo) {
    if (isPlaying && bgVideo.paused) bgVideo.play();
    if (!isPlaying && !bgVideo.paused) bgVideo.pause();

    if (Math.abs(bgVideo.currentTime - t) > 0.5) {
      bgVideo.currentTime = t;
    }
  }

  const inlineVideo = document.getElementById('inline-video');
  
  if (stage.classList.contains('mode-content-video')) {
    if (inlineVideo) {
      if (isPlaying && inlineVideo.paused) inlineVideo.play().catch(e => {});
      if (!isPlaying && !inlineVideo.paused) inlineVideo.pause();
      
      if (!slide.beat_videos || slide.beat_videos.length <= 1) {
        const singleBeat = slide.visual_beats && slide.visual_beats[0];
        const singleDisplayMode = singleBeat?.display_mode || 'video_primary';
        
        stage.classList.remove('video-swap');
        stage.classList.remove('video-focus');
        
        if (singleDisplayMode === 'video_only') {
          stage.classList.add('video-focus');
        } else if (singleDisplayMode === 'text_primary') {
          stage.classList.add('video-swap');
        }
      }
    }
    
    if (slide.beat_videos && slide.beat_videos.length > 1) {
      let targetBeatIndex = 0;
      
      if (slide.timed_segments && slide.timed_segments.length === slide.beat_videos.length) {
        for (let i = 0; i < slide.timed_segments.length; i++) {
          const seg = slide.timed_segments[i];
          if (t >= seg.start_time && t < seg.end_time) {
            targetBeatIndex = i;
            break;
          } else if (t >= seg.end_time) {
            targetBeatIndex = Math.min(i + 1, slide.beat_videos.length - 1);
          }
        }
      } else if (duration && !isNaN(duration)) {
        const beatDuration = duration / slide.beat_videos.length;
        targetBeatIndex = Math.min(Math.floor(t / beatDuration), slide.beat_videos.length - 1);
      }
      
      if (targetBeatIndex !== currentBeatIndex && inlineVideo) {
        currentBeatIndex = targetBeatIndex;
        const newBeatPath = slide.beat_videos[targetBeatIndex];
        console.log(`Switching to beat ${targetBeatIndex}: ${newBeatPath}`);
        videoBufferManager.switchTo(inlineVideo, newBeatPath, 0.7);
        videoBufferManager.preloadNext(targetBeatIndex, slide.beat_videos);
      }
      
      const activeBeat = slide.visual_beats && slide.visual_beats[targetBeatIndex];
      const beatDisplayMode = activeBeat?.display_mode || 'video_primary';
      
      stage.classList.remove('video-swap');
      stage.classList.remove('video-focus');
      
      if (beatDisplayMode === 'video_only') {
        stage.classList.add('video-focus');
      } else if (beatDisplayMode === 'text_primary') {
        stage.classList.add('video-swap');
      } else if (beatDisplayMode === 'video_primary') {
        const activeSeg = slide.timed_segments?.[targetBeatIndex];
        if (activeSeg) {
          const timeIntoSegment = t - activeSeg.start_time;
          const textShowDuration = 3.0;
          
          if (timeIntoSegment > textShowDuration) {
            stage.classList.add('video-focus');
          }
        }
      }
    }
    
    // Handle recap video sequencing - switch between 5 recap scene videos
    const sectionType = slide.section_type || slide.slide_type || 'content';
    if (sectionType === 'recap' && slide.recap_video_paths && slide.recap_video_paths.length > 1) {
      const recapScenes = (slide.visual_beats && slide.visual_beats.length > 0) ? slide.visual_beats : (slide.recap_scenes || []);
      const numScenes = slide.recap_video_paths.length;
      const sceneDuration = duration / numScenes;
      
      let targetRecapIndex = Math.min(Math.floor(t / sceneDuration), numScenes - 1);
      
      if (targetRecapIndex !== currentBeatIndex && inlineVideo) {
        currentBeatIndex = targetRecapIndex;
        const newRecapPath = slide.recap_video_paths[targetRecapIndex];
        if (newRecapPath) {
          console.log(`Switching to recap scene ${targetRecapIndex + 1}: ${newRecapPath}`);
          videoBufferManager.switchTo(inlineVideo, newRecapPath, 1.0);
          videoBufferManager.preloadNext(targetRecapIndex, slide.recap_video_paths);
        }
        
        // Update the displayed scene info if we have scene data
        if (recapScenes[targetRecapIndex]) {
          const scene = recapScenes[targetRecapIndex];
          console.log(`Recap Scene ${targetRecapIndex + 1}: ${scene.concept_title || 'Scene'}`);
        }
      }
    }
  }

  let hasActiveSegment = false;
  let activeSegmentIndex = -1;
  if (slide.timed_segments) {
    slide.timed_segments.forEach((seg, i) => {
      const el = document.getElementById(`seg-${i}`);
      if (!el) return;

      if (t >= seg.start_time && t < seg.end_time) {
        el.classList.add('active');
        el.classList.remove('read');
        hasActiveSegment = true;
        activeSegmentIndex = i;
      } else if (t >= seg.end_time) {
        el.classList.remove('active');
        el.classList.add('read');
      } else {
        el.classList.remove('active');
        el.classList.remove('read');
      }
    });
  }
  
  // ISS-160: Handle flip_timing_sec - flip from text to video mid-segment
  const activeNarrSegs = slide.narration?.segments || slide.narration_segments;
  if (activeSegmentIndex >= 0 && activeNarrSegs && activeNarrSegs[activeSegmentIndex]) {
    const activeSeg = activeNarrSegs[activeSegmentIndex];
    const flipTiming = activeSeg.display_directives?.flip_timing_sec;
    
    if (flipTiming !== null && flipTiming !== undefined && flipTiming >= 0) {
      const segStartTime = slide.timed_segments?.[activeSegmentIndex]?.start_time || 0;
      const elapsedInSeg = t - segStartTime;
      
      if (elapsedInSeg >= flipTiming && !slide._flippedSegments?.[activeSegmentIndex]) {
        // Time to flip from text to video
        slide._flippedSegments = slide._flippedSegments || {};
        slide._flippedSegments[activeSegmentIndex] = true;
        console.log(`[ISS-160] Segment ${activeSegmentIndex}: Flip triggered at ${flipTiming}s (elapsed: ${elapsedInSeg.toFixed(1)}s)`);
        
        // Apply flip: hide text, show video
        layerController.applyDirectivesImmediate({
          textLayer: 'hide',
          visualLayer: 'show',
          avatarLayer: activeSeg.display_directives?.avatar_layer || 'show',
          sectionType: slide.section_type || 'content',
          segmentIndex: activeSegmentIndex
        });
      }
    }
  }
  
  const activeNarrationSegs = slide.narration?.segments || slide.narration_segments;
  if (activeSegmentIndex >= 0 && activeNarrationSegs && activeNarrationSegs[activeSegmentIndex]) {
    const sType = slide.section_type || slide.slide_type || 'content';
    layerController.applyDirectives(activeNarrationSegs[activeSegmentIndex], sType, activeSegmentIndex);
  } else if (!hasActiveSegment && slide.timed_segments && slide.timed_segments.length > 0) {
    // ISS-133 FIX: When audio ends (past last segment), fade out text content
    const lastSeg = slide.timed_segments[slide.timed_segments.length - 1];
    if (t >= lastSeg.end_time) {
      const sType = slide.section_type || slide.slide_type || 'content';
      // Apply end-state directive: hide text, keep avatar visible
      layerController.applyDirectivesImmediate({
        textLayer: 'hide',
        visualLayer: 'show',
        avatarLayer: 'show',
        sectionType: sType,
        segmentIndex: -1  // Special index for end state
      });
    }
  }
  
  const sType = slide.section_type || slide.slide_type || 'content';
  if (sType === 'quiz' && slide.quizData && slide.timed_segments) {
    const totalSteps = slide.quizData.revealStepCount || 3;
    const correctId = slide.quizData.correctChoiceId;
    
    let activeStep = -1;
    slide.timed_segments.forEach((seg, i) => {
      const stepEl = document.getElementById(`reveal-step-${i}`);
      if (stepEl) {
        if (t >= seg.start_time && t < (seg.end_time || Infinity)) {
          stepEl.classList.add('active');
          activeStep = i;
        } else if (t >= (seg.end_time || Infinity)) {
          stepEl.classList.add('active');
          stepEl.classList.add('read');
        } else {
          stepEl.classList.remove('active');
          stepEl.classList.remove('read');
        }
      }
    });
    
    document.querySelectorAll('.quiz-choice').forEach(ch => {
      ch.classList.remove('active');
    });
    if (activeStep >= 0 && activeStep < slide.quizData.choices.length) {
      const activeChoiceId = slide.quizData.choices[activeStep]?.id;
      if (activeChoiceId) {
        const activeChoice = document.getElementById(`choice-${activeChoiceId}`);
        if (activeChoice) activeChoice.classList.add('active');
      }
    }
    
    const lastSeg = slide.timed_segments[totalSteps - 1];
    if (lastSeg && t >= lastSeg.start_time && correctId) {
      const correctChoice = document.getElementById(`choice-${correctId}`);
      if (correctChoice) {
        correctChoice.classList.add('correct');
        correctChoice.classList.remove('active');
      }
      document.querySelectorAll('.quiz-choice').forEach(ch => {
        if (ch.dataset.choiceId !== correctId) {
          ch.classList.add('incorrect');
          ch.classList.remove('active');
        }
      });
    }
  }
  
  if (stage.classList.contains('mode-content-video') && (!slide.beat_videos || slide.beat_videos.length <= 1)) {
    const singleBeat = slide.visual_beats && slide.visual_beats[0];
    const mode = singleBeat?.display_mode || 'video_primary';
    
    if (mode === 'video_primary' && slide.timed_segments) {
      const activeSeg = slide.timed_segments.find(seg => t >= seg.start_time && t < seg.end_time);
      if (activeSeg) {
        const timeIntoSegment = t - activeSeg.start_time;
        const textShowDuration = 3.0;
        
        stage.classList.remove('video-focus');
        if (timeIntoSegment > textShowDuration) {
          stage.classList.add('video-focus');
        }
      }
    }
  }

  updateSlideImages(slide, t);

  const scenes = (slide.visual_beats && slide.visual_beats.length > 0) ? slide.visual_beats : (slide.recap_scenes || slide.storyboard_scenes);
  if (scenes && scenes.length > 0 && slide.timed_segments) {
    const sectionType = slide.section_type || slide.slide_type;
    if (sectionType === 'recap') {
      const segmentDuration = duration / scenes.length;
      scenes.forEach((scene, i) => {
        const sceneStart = i * segmentDuration;
        const sceneEnd = (i + 1) * segmentDuration;
        if (t >= sceneStart && t < sceneEnd) {
          const bg = document.getElementById('bg-image-layer');
          const label = document.getElementById('scene-label');

          if (scene.image_url && !bg.src.includes(scene.image_url)) {
            bg.src = scene.image_url;
            bg.style.opacity = 1;
          }
          if (label) {
            label.innerText = scene.concept_title || scene.description || `Scene ${i + 1}`;
          }
        }
      });
    }
  }
}

audio.addEventListener('timeupdate', handleTimeUpdate);
video.addEventListener('timeupdate', handleTimeUpdate);

function handleEnded(e) {
  if (e.target !== currentMedia) return;
  if (lessonData && currentSlideIndex < lessonData.slides.length - 1) {
    setTimeout(() => loadSlide(currentSlideIndex + 1), 1000);
  }
}
audio.addEventListener('ended', handleEnded);
video.addEventListener('ended', handleEnded);

// Handle inline video ended - show text content again
const inlineVideoEl = document.getElementById('inline-video');
if (inlineVideoEl) {
  inlineVideoEl.addEventListener('ended', () => {
    stage.classList.remove('video-focus');
    stage.classList.remove('video-swap');
    console.log('Inline video ended - showing content');
  });
}

function formatTime(s) {
  return `${Math.floor(s / 60)}:${Math.floor(s % 60).toString().padStart(2, '0')}`;
}

function togglePlay() {
  const bgVideo = document.getElementById('scene-video');
  
  if (currentMedia.paused) {
    currentMedia.play();
    if (currentMedia === audio) video.play();
    if (bgVideo && bgVideo.src && (stage.classList.contains('mode-khan') || stage.classList.contains('mode-content-video'))) {
      bgVideo.play().catch(e => {});
    }

    isPlaying = true;
    document.getElementById('btn-play').innerText = "Pause";
  } else {
    currentMedia.pause();
    if (currentMedia === audio) video.pause();
    if (bgVideo && !bgVideo.paused) {
      bgVideo.pause();
    }

    isPlaying = false;
    document.getElementById('btn-play').innerText = "Play";
  }
}

function prevSlide() {
  if (currentSlideIndex > 0) loadSlide(currentSlideIndex - 1);
}

function nextSlide() {
  if (lessonData && currentSlideIndex < lessonData.slides.length - 1) loadSlide(currentSlideIndex + 1);
}

document.getElementById('btn-play').onclick = togglePlay;
document.getElementById('btn-prev').onclick = prevSlide;
document.getElementById('btn-next').onclick = nextSlide;
document.getElementById('btn-dev').onclick = () => {
  document.getElementById('dev-panel').classList.toggle('show');
  document.getElementById('dev-stats-overlay').classList.toggle('visible');
  updateDevStats();
};
document.getElementById('btn-fullscreen').onclick = toggleFullScreen;

function toggleFullScreen() {
  if (!document.fullscreenElement) {
    stage.requestFullscreen().catch(err => {
      alert(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
    });
  } else {
    document.exitFullscreen();
  }
}

document.getElementById('progress-container').onclick = (e) => {
  const rect = e.target.getBoundingClientRect();
  const pct = (e.clientX - rect.left) / rect.width;
  if (currentMedia.duration && !isNaN(currentMedia.duration)) {
    currentMedia.currentTime = pct * currentMedia.duration;
    if (currentMedia === audio && video.duration) {
      video.currentTime = pct * video.duration;
    }
  }
};

document.addEventListener('keydown', (e) => {
  if (e.code === 'Space') { e.preventDefault(); togglePlay(); }
  if (e.code === 'ArrowLeft') prevSlide();
  if (e.code === 'ArrowRight') nextSlide();
  if (e.code === 'KeyD') {
    document.getElementById('dev-panel').classList.toggle('show');
    document.getElementById('dev-stats-overlay').classList.toggle('visible');
    updateDevStats();
  }
});

function buildSlideList() {
  const container = document.getElementById('slide-list');
  container.innerHTML = '';
  if (!lessonData || !lessonData.slides) return;
  
  lessonData.slides.forEach((slide, i) => {
    const div = document.createElement('div');
    const sectionType = slide.section_type || slide.slide_type || 'content';
    div.className = 'slide-thumb' + (i === 0 ? ' active' : '');
    div.innerHTML = `<div class="num">${i + 1}</div><div class="type">${sectionType}</div>`;
    div.onclick = () => loadSlide(i);
    container.appendChild(div);
  });
}

async function checkExistingPresentation() {
  try {
    const response = await fetch(BASE_PATH + 'presentation.json');
    if (response.ok) {
      lessonData = await response.json();
      
      if (!lessonData.slides) {
        if (lessonData.sections) {
          lessonData.slides = lessonData.sections.map(section => {
            const sectionId = section.section_id || section.id;
            
            const narrationSegs = section.narration?.segments || section.narration_segments || [];
            let timed_segments = null;
            if (narrationSegs.length > 0) {
              let cumulativeTime = 0;
              timed_segments = narrationSegs.map(seg => {
                const duration = seg.duration_seconds || seg.duration || 4;
                const start = cumulativeTime;
                cumulativeTime += duration;
                return {
                  visual: seg.text || '',
                  start_time: start,
                  end_time: cumulativeTime
                };
              });
            }
            
            const recapScenes = (section.visual_beats && section.visual_beats.length > 0) ? section.visual_beats : (section.recap_scenes || []);
            const memoryCards = (section.visual_beats && section.visual_beats.length > 0) ? section.visual_beats : section.flashcards;
            
            const aggregatedVisualContent = section.visual_content || {};
            if (narrationSegs && narrationSegs.length > 0) {
              const allBullets = [];
              narrationSegs.forEach(seg => {
                if (seg.visual_content && seg.visual_content.bullet_points) {
                  allBullets.push(...seg.visual_content.bullet_points);
                }
              });
              if (allBullets.length > 0) {
                aggregatedVisualContent.bullet_points = allBullets;
              }
            }
            
            // ISS-061/ISS-064 FIX: Prefer video_path metadata, fallback to pattern-based detection
            let contentVideoPath = null;
            let hasContentVideo = false;
            let recapVideoPaths = [];
            
            // Priority 1: Use video_path metadata from pipeline if available
            if (section.video_path) {
              contentVideoPath = section.video_path.startsWith('/') ? section.video_path : BASE_PATH + section.video_path;
              hasContentVideo = true;
            } 
            // Priority 2: For recap sections - ISS-069 FIX: prefer section-level recap_video_paths first
            else if (section.section_type === 'recap') {
              hasContentVideo = true;
              
              // ISS-069: Check section-level recap_video_paths FIRST (from pipeline)
              if (section.recap_video_paths && section.recap_video_paths.length > 0) {
                recapVideoPaths = section.recap_video_paths.map(p => {
                  return p.startsWith('/') ? p : BASE_PATH + p;
                });
                contentVideoPath = recapVideoPaths[0];
                console.log(`[ISS-069] Using section-level recap_video_paths: ${recapVideoPaths.length} scenes`);
              }
              // Fallback: Check visual_beats video_path
              else if (recapScenes.length > 0 && recapScenes[0] && recapScenes[0].video_path) {
                recapVideoPaths = recapScenes.map((s, i) => {
                  if (s.video_path) {
                    return s.video_path.startsWith('/') ? s.video_path : BASE_PATH + s.video_path;
                  }
                  return BASE_PATH + `videos/recap_${sectionId}_scene_${s.scene_id || s.scene || i+1}.mp4`;
                });
                contentVideoPath = recapVideoPaths[0];
              }
              // Last fallback: Default to single video
              else {
                contentVideoPath = BASE_PATH + `videos/topic_${sectionId}.mp4`;
                recapVideoPaths = [contentVideoPath];
              }
            }
            // Priority 3: For content with video renderer, use topic_<id>.mp4
            else if (section.renderer === 'wan_video' || section.renderer === 'manim' || section.renderer === 'video') {
              contentVideoPath = BASE_PATH + `videos/topic_${sectionId}.mp4`;
              hasContentVideo = true;
            }
            
            // ISS-093 FIX: Use beat_videos from presentation.json if available
            let beatVideos = [];
            if (section.beat_videos && section.beat_videos.length > 0) {
              beatVideos = section.beat_videos.map(p => {
                // Normalize path - avoid double prefixing
                if (p.startsWith('/')) return p;
                if (p.startsWith('videos/')) return BASE_PATH + p;
                return BASE_PATH + 'videos/' + p;
              });
              console.log(`[ISS-093] Using section-level beat_videos: ${beatVideos.length} beats, first: ${beatVideos[0]}`);
              // Update content_video_path to first beat if not already set
              if (!contentVideoPath && beatVideos.length > 0) {
                contentVideoPath = beatVideos[0];
                hasContentVideo = true;
              }
            }
            
            return {
              slide_number: sectionId,
              section_type: section.section_type || 'content',
              slide_type: section.section_type || 'content',
              title: section.title,
              segments: section.segments,
              flashcards: memoryCards,
              recap_scenes: recapScenes,
              visual_beats: section.visual_beats || [],
              narration_segments: narrationSegs,
              narration: section.narration,
              timed_segments: timed_segments,
              audio_path: BASE_PATH + `audio/section_${sectionId}.mp3`,
              video_path: section.video_path,
              content_video_path: contentVideoPath,
              has_content_video: hasContentVideo || section.has_content_video,
              recap_video_paths: recapVideoPaths,
              section_id: sectionId,
              id: sectionId,
              beat_videos: beatVideos,
              audio_duration: section.duration,
              full_narration: section.narration,
              visual_content: aggregatedVisualContent,
              renderer_reasoning: section.renderer_reasoning || null,
              layout: section.layout || section.avatar_layout
            };
          });
        } else if (lessonData.topics) {
          lessonData.slides = lessonData.topics.map(topic => ({
            slide_number: topic.id,
            slide_type: 'content',
            section_type: 'content',
            title: topic.title,
            segments: topic.segments,
            timed_segments: topic.segments ? topic.segments.map(s => ({
              visual: s.text,
              start_time: s.start,
              end_time: s.start + s.duration
            })) : [],
            audio_path: BASE_PATH + `audio/topic_${topic.id}.mp3`,
            audio_duration: topic.duration,
            full_narration: topic.narration,
            visual_content: { bullet_points: topic.segments ? topic.segments.map(s => s.text) : [] }
          }));
        }
      }
      
      if (lessonData.slides && lessonData.slides.length > 0) {
        document.getElementById('upload-overlay').classList.add('hidden');
        buildSlideList();
        
        let startSlide = 0;
        const hashMatch = window.location.hash.match(/#slide(\d+)/);
        if (hashMatch) {
          startSlide = Math.max(0, Math.min(parseInt(hashMatch[1]) - 1, lessonData.slides.length - 1));
        }
        
        loadSlide(startSlide);
        updateVisuals();
        
        detectRemainingVideosInBackground(startSlide);
      } else {
        document.getElementById('upload-overlay').classList.remove('hidden');
      }
    } else {
      document.getElementById('upload-overlay').classList.remove('hidden');
    }
  } catch (e) {
    console.log('No existing presentation found');
    document.getElementById('upload-overlay').classList.remove('hidden');
  }
}

async function detectRemainingVideosInBackground(skipIndex) {
  for (let i = 0; i < lessonData.slides.length; i++) {
    if (i === skipIndex) continue;
    await detectVideosForSlide(lessonData.slides[i]);
  }
}

let currentJobId = null;
let pollInterval = null;

async function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('subject', document.getElementById('subjectSelect').value);
  formData.append('grade', document.getElementById('gradeSelect').value);

  showLoading();

  try {
    const response = await fetch('/submit_job', {
      method: 'POST',
      body: formData
    });

    const result = await response.json();

    if (result.status === 'accepted' && result.job_id) {
      currentJobId = result.job_id;
      startPolling(result.job_id);
    } else if (result.status === 'busy') {
      alert('Another job is already processing. Please wait and try again.');
      location.reload();
    } else {
      alert('Job submission failed: ' + (result.error || 'Unknown error'));
      location.reload();
    }
  } catch (e) {
    alert('Upload failed: ' + e.message);
    location.reload();
  }
}

function showLoading() {
  document.getElementById('upload-box').innerHTML = `
    <div class="spinner"></div>
    <p>Processing your content...</p>
    <div class="progress-container">
      <div class="progress-bar">
        <div class="progress-fill" id="job-progress" style="width: 0%"></div>
      </div>
      <div class="progress-text" id="progress-text">Initializing...</div>
      <div class="step-indicator" id="step-indicator"></div>
    </div>
  `;
}

function updateProgress(status) {
  const progressBar = document.getElementById('job-progress');
  const progressText = document.getElementById('progress-text');
  const stepIndicator = document.getElementById('step-indicator');
  
  if (progressBar) progressBar.style.width = status.progress + '%';
  if (progressText) progressText.textContent = status.current_step || 'Processing...';
  if (stepIndicator) stepIndicator.textContent = `Step ${status.steps_completed + 1} of ${status.total_steps}`;
}

function startPolling(jobId) {
  if (pollInterval) clearInterval(pollInterval);
  
  pollInterval = setInterval(async () => {
    try {
      const response = await fetch(`/job/${jobId}/status`);
      const status = await response.json();
      
      updateProgress(status);
      
      if (status.status === 'completed') {
        clearInterval(pollInterval);
        pollInterval = null;
        // Redirect to job-specific player URL so assets load from job folder
        window.location.href = `/jobs/${jobId}/`;
      } else if (status.status === 'failed') {
        clearInterval(pollInterval);
        pollInterval = null;
        alert('Processing failed: ' + (status.error || 'Unknown error'));
        location.reload();
      }
    } catch (e) {
      console.error('Polling error:', e);
    }
  }, 1500);
}

function useSampleContent() {
  const sampleMarkdown = `# Introduction to Photosynthesis

## What is Photosynthesis?
Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods from carbon dioxide and water.

## The Process
Plants absorb carbon dioxide from the air through tiny pores called stomata. Water is absorbed by roots from the soil. Using the energy from sunlight captured by chlorophyll, plants convert these into glucose and oxygen.

## The Equation
The chemical equation for photosynthesis is:
6CO2 + 6H2O + Light Energy → C6H12O6 + 6O2

## Importance
Photosynthesis is essential for life on Earth as it produces the oxygen we breathe and forms the base of the food chain.`;

  const subject = document.getElementById('subjectSelect').value;
  const grade = document.getElementById('gradeSelect').value;

  showLoading();

  fetch('/submit_job', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      markdown: sampleMarkdown,
      subject: subject,
      grade: grade
    })
  })
    .then(response => response.json())
    .then(result => {
      if (result.status === 'accepted' && result.job_id) {
        currentJobId = result.job_id;
        startPolling(result.job_id);
      } else if (result.status === 'busy') {
        alert('Another job is already processing. Please wait and try again.');
        location.reload();
      } else {
        alert('Job submission failed: ' + (result.error || 'Unknown error'));
        location.reload();
      }
    })
    .catch(e => {
      alert('Processing failed: ' + e.message);
      location.reload();
    });
}

document.getElementById('fileInput').addEventListener('change', handleFileUpload);

function showNewContentOverlay() {
  lessonData = null;
  currentSlideIndex = 0;
  
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
  
  document.getElementById('upload-box').innerHTML = `
    <h2>AI Animated Education</h2>
    <p>Upload PDF or Markdown file to generate educational videos</p>
    <input type="file" id="fileInput" accept=".pdf,.md,.markdown,.txt" style="display:none">
    <div style="margin-bottom: 15px;">
      <button class="upload-btn" onclick="document.getElementById('fileInput').click()">Upload PDF or Markdown</button>
    </div>
    <button class="upload-btn" style="background:#333" onclick="useSampleContent()">Try Sample Content</button>
    <div class="upload-selects">
      <select id="subjectSelect">
        <option value="General Science">General Science</option>
        <option value="Mathematics">Mathematics</option>
        <option value="Physics">Physics</option>
        <option value="Chemistry">Chemistry</option>
        <option value="Biology">Biology</option>
      </select>
      <select id="gradeSelect">
        <option value="8">Grade 8</option>
        <option value="9" selected>Grade 9</option>
        <option value="10">Grade 10</option>
      </select>
    </div>
    <p style="color:#666; font-size:0.8rem; margin-top:15px;">Supports: .pdf, .md, .markdown, .txt files</p>
  `;
  
  document.getElementById('fileInput').addEventListener('change', handleFileUpload);
  
  document.getElementById('upload-overlay').classList.remove('hidden');
}

document.getElementById('btn-new').onclick = showNewContentOverlay;

document.addEventListener('DOMContentLoaded', () => {
  videoBufferManager.init();
  checkExistingPresentation();
  updateVisuals();
  setupContentOverflowHandler();
});
