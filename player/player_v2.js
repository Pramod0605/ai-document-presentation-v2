/**
 * PLAYER V2 - Clean Unified Renderer
 * No legacy code - fresh implementation
 */

// ============================================
// CONFIGURATION
// ============================================
const AVATAR_URL = "/player/assets/avatar_placeholder.mp4";
const PRESENTATION_PATH = "presentation.json";

// ============================================
// STATE
// ============================================
let lessonData = null;
let slides = [];
let currentSlideIndex = 0;
let isPlaying = false;
let currentSegmentIndex = 0;

// DOM Elements
let stage, contentLayer, contentBox, avatarLayer, avatarVideo;
let videoLayer, contentVideo, narrationAudio;
let btnPlay, btnPrev, btnNext, slidePicker;
let timelineFill, timelineHandle, timeDisplay;

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', init);

async function init() {
  cacheDOMElements();
  setupEventListeners();
  await loadPresentation();
}

function cacheDOMElements() {
  stage = document.getElementById('stage');
  contentLayer = document.getElementById('content-layer');
  contentBox = document.getElementById('content-box');
  avatarLayer = document.getElementById('avatar-layer');
  avatarVideo = document.getElementById('avatar-video');
  videoLayer = document.getElementById('video-layer');
  contentVideo = document.getElementById('content-video');
  narrationAudio = document.getElementById('narration-audio');
  btnPlay = document.getElementById('btn-play');
  btnPrev = document.getElementById('btn-prev');
  btnNext = document.getElementById('btn-next');
  slidePicker = document.getElementById('slide-picker');
  timelineFill = document.getElementById('timeline-fill');
  timelineHandle = document.getElementById('timeline-handle');
  timeDisplay = document.getElementById('time-display');
}

function setupEventListeners() {
  btnPlay.addEventListener('click', togglePlay);
  btnPrev.addEventListener('click', prevSlide);
  btnNext.addEventListener('click', nextSlide);
  slidePicker.addEventListener('change', (e) => loadSlide(parseInt(e.target.value)));
  
  narrationAudio.addEventListener('timeupdate', updateTimeline);
  narrationAudio.addEventListener('ended', onSlideEnd);
  contentVideo.addEventListener('ended', onContentVideoEnd);
  
  document.getElementById('timeline-track').addEventListener('click', seekTimeline);
  document.getElementById('btn-fullscreen').addEventListener('click', toggleFullscreen);
  
  document.addEventListener('keydown', handleKeyboard);
  
  // Avatar video setup with error handling
  avatarVideo.onerror = (e) => {
    console.error('Avatar video error:', e, avatarVideo.error);
  };
  avatarVideo.onloadeddata = () => {
    console.log('Avatar video loaded successfully');
    avatarVideo.play().catch(e => console.log('Avatar autoplay blocked:', e));
  };
  
  avatarVideo.src = AVATAR_URL;
  avatarVideo.muted = true;
  avatarVideo.loop = true;
  avatarVideo.load();
}

async function loadPresentation() {
  try {
    const response = await fetch(PRESENTATION_PATH);
    lessonData = await response.json();
    slides = lessonData.sections || [];
    
    populateSlidePicker();
    
    if (slides.length > 0) {
      loadSlide(0);
    }
  } catch (error) {
    console.error('Failed to load presentation:', error);
    contentBox.innerHTML = '<p style="color: #f87171;">Failed to load presentation. Check console for details.</p>';
  }
}

function populateSlidePicker() {
  slidePicker.innerHTML = '';
  slides.forEach((slide, i) => {
    const option = document.createElement('option');
    option.value = i;
    option.textContent = `${i + 1}. ${slide.section_type}: ${slide.title || 'Untitled'}`.substring(0, 40);
    slidePicker.appendChild(option);
  });
}

// ============================================
// SLIDE RENDERER (Main Entry Point)
// ============================================
function loadSlide(index) {
  if (index < 0 || index >= slides.length) return;
  
  currentSlideIndex = index;
  currentSegmentIndex = 0;
  slidePicker.value = index;
  
  const slide = slides[index];
  const sectionType = slide.section_type || 'content';
  
  console.log(`[V2] Loading slide ${index + 1}: ${sectionType} - ${slide.title || 'Untitled'}`);
  
  contentBox.innerHTML = '';
  videoLayer.classList.add('hidden');
  
  setStageMode(sectionType);
  
  switch (sectionType) {
    case 'intro':
      renderIntro(slide);
      break;
    case 'summary':
      renderSummary(slide);
      break;
    case 'quiz':
      renderQuiz(slide);
      break;
    case 'memory':
      renderMemory(slide);
      break;
    case 'recap':
      renderRecap(slide);
      break;
    case 'content':
    case 'example':
    default:
      renderContent(slide);
      break;
  }
  
  setupAudio(slide);
  
  if (window.MathJax) {
    MathJax.typesetPromise().catch(() => {});
  }
  
  requestAnimationFrame(() => {
    fitContentToContainer(contentBox);
  });
}

function setStageMode(sectionType) {
  stage.className = '';
  
  if (sectionType === 'intro') {
    stage.classList.add('mode-intro');
    contentLayer.classList.add('hidden');
  } else {
    contentLayer.classList.remove('hidden');
  }
}

// ============================================
// SECTION RENDERERS
// ============================================

function renderIntro(slide) {
  console.log('[V2] IntroRenderer: Avatar only, no content');
}

function renderSummary(slide) {
  console.log('[V2] SummaryRenderer: Level-1 bullets with checkmarks');
  
  const segments = slide.narration?.segments || [];
  const allBullets = [];
  
  segments.forEach(seg => {
    const vc = seg.visual_content;
    if (vc?.bullet_points) {
      vc.bullet_points.forEach(bp => {
        if (!bp.level || bp.level === 1) {
          allBullets.push(sanitizeMarkdown(bp.text || bp));
        }
      });
    }
  });
  
  if (allBullets.length === 0) {
    contentBox.innerHTML = '<p class="paragraph-block">Summary content</p>';
    return;
  }
  
  const list = document.createElement('ul');
  list.className = 'summary-list';
  
  allBullets.forEach((text, i) => {
    const item = document.createElement('li');
    item.className = 'summary-item';
    item.id = `seg-${i}`;
    item.innerHTML = `
      <span class="summary-marker">✓</span>
      <span class="summary-text">${text}</span>
    `;
    list.appendChild(item);
  });
  
  contentBox.appendChild(list);
}

function renderContent(slide) {
  console.log('[V2] ContentRenderer: Paragraphs, bullets, formulas');
  
  const segments = slide.narration?.segments || [];
  
  if (segments.length === 0) {
    const vc = slide.visual_content;
    if (vc) {
      renderVisualContent(vc, contentBox);
    }
    return;
  }
  
  segments.forEach((seg, i) => {
    const segDiv = document.createElement('div');
    segDiv.className = 'segment-block';
    segDiv.id = `seg-${i}`;
    
    const vc = seg.visual_content;
    if (vc) {
      renderVisualContent(vc, segDiv);
    } else if (seg.text) {
      const para = document.createElement('div');
      para.className = 'paragraph-block';
      para.innerHTML = sanitizeMarkdown(seg.text);
      segDiv.appendChild(para);
    }
    
    if (segDiv.children.length > 0) {
      contentBox.appendChild(segDiv);
    }
  });
  
  const firstSeg = document.getElementById('seg-0');
  if (firstSeg) firstSeg.classList.add('segment-active');
}

function renderVisualContent(vc, container) {
  const contentType = vc.content_type || 'paragraph';
  
  if (vc.verbatim_text) {
    const para = document.createElement('div');
    para.className = 'paragraph-block';
    para.innerHTML = sanitizeMarkdown(vc.verbatim_text);
    container.appendChild(para);
  }
  
  if (vc.bullet_points && vc.bullet_points.length > 0) {
    const list = document.createElement('ul');
    list.className = 'bullet-list';
    
    vc.bullet_points.forEach(bp => {
      const item = document.createElement('li');
      item.className = 'bullet-item';
      if (bp.level && bp.level > 1) {
        item.classList.add(`level-${bp.level}`);
      }
      
      const markers = ['•', '○', '◦', '◇'];
      const level = bp.level || 1;
      const marker = markers[Math.min(level - 1, markers.length - 1)];
      
      item.innerHTML = `
        <span class="bullet-marker">${marker}</span>
        <span class="bullet-text">${sanitizeMarkdown(bp.text || bp)}</span>
      `;
      list.appendChild(item);
    });
    
    container.appendChild(list);
  }
  
  if (vc.ordered_list && vc.ordered_list.length > 0) {
    const list = document.createElement('ol');
    list.className = 'ordered-list';
    
    vc.ordered_list.forEach((text, i) => {
      const item = document.createElement('li');
      item.className = 'ordered-item';
      item.innerHTML = `
        <span class="ordered-number">${i + 1}.</span>
        <span>${sanitizeMarkdown(text)}</span>
      `;
      list.appendChild(item);
    });
    
    container.appendChild(list);
  }
  
  if (vc.formula || vc.formulas) {
    const formulas = vc.formulas || [vc.formula];
    formulas.forEach(f => {
      const block = document.createElement('div');
      block.className = 'formula-block';
      block.innerHTML = f;
      container.appendChild(block);
    });
  }
}

function renderQuiz(slide) {
  console.log('[V2] QuizRenderer: Question + choices');
  
  const segments = slide.narration?.segments || [];
  let question = '';
  const choices = [];
  
  segments.forEach(seg => {
    const vc = seg.visual_content;
    if (vc?.bullet_points) {
      vc.bullet_points.forEach(bp => {
        if (bp.level === 1) {
          question = bp.text.replace(/^Question\s*\d+:\s*/i, '');
        } else if (bp.level === 2) {
          const match = bp.text.match(/^([A-D])\)\s*(.+)$/i);
          if (match) {
            choices.push({ letter: match[1].toUpperCase(), text: match[2] });
          } else {
            choices.push({ letter: String.fromCharCode(65 + choices.length), text: bp.text });
          }
        }
      });
    }
  });
  
  const card = document.createElement('div');
  card.className = 'quiz-card';
  
  if (question) {
    const qDiv = document.createElement('div');
    qDiv.className = 'quiz-question';
    qDiv.innerHTML = sanitizeMarkdown(question);
    card.appendChild(qDiv);
  }
  
  if (choices.length > 0) {
    const choicesDiv = document.createElement('div');
    choicesDiv.className = 'quiz-choices';
    
    choices.forEach(c => {
      const choice = document.createElement('div');
      choice.className = 'quiz-choice';
      choice.innerHTML = `
        <span class="choice-letter">${c.letter}</span>
        <span class="choice-text">${sanitizeMarkdown(c.text)}</span>
      `;
      choicesDiv.appendChild(choice);
    });
    
    card.appendChild(choicesDiv);
  }
  
  contentBox.appendChild(card);
}

function renderMemory(slide) {
  console.log('[V2] MemoryRenderer: Flashcards');
  
  const flashcards = slide.visual_content?.flashcards || [];
  
  if (flashcards.length === 0) {
    const segments = slide.narration?.segments || [];
    segments.forEach((seg, i) => {
      const card = document.createElement('div');
      card.className = 'flashcard';
      card.id = `seg-${i}`;
      card.innerHTML = `
        <div class="flashcard-title">${sanitizeMarkdown(seg.text || '')}</div>
      `;
      contentBox.appendChild(card);
    });
    return;
  }
  
  const container = document.createElement('div');
  container.className = 'flashcard-container';
  
  flashcards.forEach((fc, i) => {
    const card = document.createElement('div');
    card.className = 'flashcard';
    card.id = `seg-${i}`;
    card.innerHTML = `
      <div class="flashcard-letter">${fc.letter || ''}</div>
      <div class="flashcard-title">${fc.title || ''}</div>
      ${fc.mnemonic ? `<div class="flashcard-mnemonic">${fc.mnemonic}</div>` : ''}
    `;
    container.appendChild(card);
  });
  
  contentBox.appendChild(container);
  
  const firstCard = document.querySelector('.flashcard');
  if (firstCard) firstCard.classList.add('active');
}

function renderRecap(slide) {
  console.log('[V2] RecapRenderer: Video focus');
  
  const videoPath = slide.content_video_path || slide.video_path;
  
  if (videoPath) {
    videoLayer.classList.remove('hidden');
    contentVideo.src = videoPath;
    contentVideo.load();
  } else {
    renderContent(slide);
  }
}

// ============================================
// AUDIO & PLAYBACK
// ============================================
function setupAudio(slide) {
  const audioPath = slide.audio_path || '';
  
  if (audioPath) {
    narrationAudio.src = audioPath;
    narrationAudio.load();
  } else {
    narrationAudio.src = '';
  }
  
  updateTimeDisplay(0, getTotalDuration(slide));
}

function getTotalDuration(slide) {
  if (slide.audio_duration) return slide.audio_duration;
  
  const segments = slide.narration?.segments || [];
  let total = 0;
  segments.forEach(seg => {
    total += seg.duration_seconds || 5;
  });
  return total || 30;
}

function togglePlay() {
  isPlaying = !isPlaying;
  
  const iconPlay = btnPlay.querySelector('.icon-play');
  const iconPause = btnPlay.querySelector('.icon-pause');
  
  if (isPlaying) {
    iconPlay.classList.add('hidden');
    iconPause.classList.remove('hidden');
    
    if (narrationAudio.src) {
      narrationAudio.play().catch(() => {});
    }
    avatarVideo.play().catch(() => {});
    
    if (!videoLayer.classList.contains('hidden')) {
      contentVideo.play().catch(() => {});
    }
  } else {
    iconPlay.classList.remove('hidden');
    iconPause.classList.add('hidden');
    
    narrationAudio.pause();
    contentVideo.pause();
  }
}

function updateTimeline() {
  const current = narrationAudio.currentTime;
  const total = narrationAudio.duration || 1;
  const percent = (current / total) * 100;
  
  timelineFill.style.width = `${percent}%`;
  timelineHandle.style.left = `${percent}%`;
  
  updateTimeDisplay(current, total);
  updateActiveSegment(current);
}

function updateTimeDisplay(current, total) {
  const formatTime = (t) => {
    const m = Math.floor(t / 60);
    const s = Math.floor(t % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };
  
  timeDisplay.textContent = `${formatTime(current)} / ${formatTime(total)}`;
}

function updateActiveSegment(currentTime) {
  const slide = slides[currentSlideIndex];
  const segments = slide.narration?.segments || [];
  
  let cumulative = 0;
  let activeIndex = 0;
  
  for (let i = 0; i < segments.length; i++) {
    const duration = segments[i].duration_seconds || 5;
    if (currentTime >= cumulative && currentTime < cumulative + duration) {
      activeIndex = i;
      break;
    }
    cumulative += duration;
  }
  
  if (activeIndex !== currentSegmentIndex) {
    const prevSeg = document.getElementById(`seg-${currentSegmentIndex}`);
    if (prevSeg) prevSeg.classList.remove('segment-active');
    
    const newSeg = document.getElementById(`seg-${activeIndex}`);
    if (newSeg) newSeg.classList.add('segment-active');
    
    currentSegmentIndex = activeIndex;
  }
}

function seekTimeline(e) {
  const track = e.currentTarget;
  const rect = track.getBoundingClientRect();
  const percent = (e.clientX - rect.left) / rect.width;
  
  if (narrationAudio.duration) {
    narrationAudio.currentTime = percent * narrationAudio.duration;
  }
}

function onSlideEnd() {
  if (currentSlideIndex < slides.length - 1) {
    setTimeout(() => loadSlide(currentSlideIndex + 1), 500);
  } else {
    isPlaying = false;
    btnPlay.querySelector('.icon-play').classList.remove('hidden');
    btnPlay.querySelector('.icon-pause').classList.add('hidden');
  }
}

function onContentVideoEnd() {
  videoLayer.classList.add('hidden');
  if (narrationAudio.src && !narrationAudio.ended) {
    narrationAudio.play().catch(() => {});
  }
}

// ============================================
// NAVIGATION
// ============================================
function prevSlide() {
  if (currentSlideIndex > 0) {
    loadSlide(currentSlideIndex - 1);
  }
}

function nextSlide() {
  if (currentSlideIndex < slides.length - 1) {
    loadSlide(currentSlideIndex + 1);
  }
}

function handleKeyboard(e) {
  switch (e.key) {
    case ' ':
      e.preventDefault();
      togglePlay();
      break;
    case 'ArrowLeft':
      prevSlide();
      break;
    case 'ArrowRight':
      nextSlide();
      break;
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  } else {
    document.exitFullscreen();
  }
}

// ============================================
// UTILITIES
// ============================================
function sanitizeMarkdown(text) {
  if (!text || typeof text !== 'string') return text;
  
  return text
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\s*#{1,6}\s*$/gm, '')
    .replace(/^(.+)\n[=]{2,}\s*$/gm, '$1')
    .replace(/^(.+)\n[-]{2,}\s*$/gm, '$1')
    .replace(/\*{1,2}([^*]+)\*{1,2}/g, '$1')
    .replace(/_{1,2}([^_]+)_{1,2}/g, '$1')
    .replace(/^>\s*/gm, '')
    .replace(/`([^`]+)`/g, '$1')
    .trim();
}

function fitContentToContainer(element, options = {}) {
  const { minScale = 0.65, maxScale = 1.0, step = 0.05 } = options;
  
  if (!element || !element.parentElement) return;
  
  const container = element.parentElement;
  let scale = maxScale;
  
  element.style.fontSize = '';
  element.style.lineHeight = '';
  
  const checkOverflow = () => {
    return element.scrollHeight > container.clientHeight;
  };
  
  while (checkOverflow() && scale > minScale) {
    scale -= step;
    element.style.fontSize = `${scale}em`;
    element.style.lineHeight = `${1.4 + (1 - scale) * 0.2}`;
  }
  
  if (checkOverflow()) {
    element.style.overflowY = 'auto';
  }
  
  console.log(`[V2] Content scaled to ${(scale * 100).toFixed(0)}%`);
}
