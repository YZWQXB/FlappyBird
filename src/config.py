"""FlappyBird 全局配置：唯一的常量与可调参数来源。"""

from __future__ import annotations

from pathlib import Path

# ---------- 路径 ----------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RES_DIR = PROJECT_ROOT / "res"
IMAGES_DIR = RES_DIR / "images"
AUDIOS_DIR = RES_DIR / "audios"
SAVE_DIR = PROJECT_ROOT / "save"
SAVE_FILE = SAVE_DIR / "highscore.json"

# ---------- 画面与循环 ----------
LOGICAL_W, LOGICAL_H = 288, 512
SCALE = 2                      # 首选窗口倍率；实际取 fit_scale() 的返回值
FORCE_SCALE = 0                # >0 时强制使用该倍率（调试/演示用）
TITLEBAR_RESERVE = 48          # 估算标题栏+任务栏预留（逻辑像素）
FPS = 60
FIXED_DT = 1 / 60
MAX_STEPS_PER_FRAME = 5
MAX_FRAME_DT = 0.25
TITLE = "FlappyBird"

# ---------- 物理 ----------
GRAVITY = 1500.0               # px/s^2（上升段基准重力）
FLAP_VELOCITY = -380.0         # px/s
MAX_FALL_SPEED = 480.0         # px/s（终端下落速度：原 640 过于"直坠"）

# 非对称重力：下降比上升更"轻"，且接近顶点时进一步减弱，形成短暂悬停
GRAVITY_FALL_SCALE = 0.65      # 下降段重力 = GRAVITY × 该系数
HANG_VY_THRESHOLD = 120.0      # |vy| 小于该值时进入"顶点滞空"过渡区
HANG_GRAVITY_SCALE = 0.35      # 顶点处重力 = GRAVITY × 该系数（线性过渡到 1.0）

HOP = FLAP_VELOCITY ** 2 / (2 * GRAVITY)   # 派生：上升段理论升高 ≈ 48.1 px

BIRD_X = 64
BIRD_Y0 = 256
BIRD_W, BIRD_H = 34, 24
BIRD_INSET = 3
HITBOX_W = BIRD_W - 2 * BIRD_INSET          # 28
HITBOX_H = BIRD_H - 2 * BIRD_INSET          # 18
BIRD_FLOAT_AMP = 5.0
BIRD_FLOAT_W = 2.4            # rad/s，待机浮动角速度
FLAP_FRAME_TIME = 0.1         # 翅膀帧切换间隔 s
ROTATE_SPRITE = True
ROTATE_MIN_DEG = -25.0
ROTATE_MAX_DEG = 90.0
ROTATE_VY_FULL = 400.0        # vy >= 该值时角度 = ROTATE_MAX_DEG
ROTATE_CACHE_MAX = 160        # 旋转帧缓存上限（防内存增长）

# ---------- 难度 ----------
BASE_SPEED = 120.0            # px/s
LEVEL_EVERY = 5               # 每 5 分升一级
MAX_LEVEL = 6
SPEED_STEP = 0.08             # 每级 +8% 速度
BASE_GAP = 110                # 0 级缝隙高度
GAP_STEP = 5                  # 每级 -5px
MIN_GAP = 80                  # 最窄缝隙

# ---------- 管道与地面 ----------
PIPE_W = 52
PIPE_CAP_H = 25
PIPE_BODY_W = 48
PIPE_BODY_X = 2               # body 相对图片的左偏移
PIPE_SPACING = 150            # 按距离生成，px
PIPE_MARGIN = 48              # 缝隙中心离顶部/地面的最小距离
MAX_CENTER_DELTA = 120        # 相邻缝隙中心最大落差
PIPE_SPAWN_X = LOGICAL_W + 10

LAND_Y = 400
LAND_H = 112
LAND_TILE_W = 336             # 地面素材宽度，平铺周期（独立于 PIPE_W）

# ---------- 主题（昼夜/鸟色） ----------
THEME_EVERY = 10              # 每 10 分换一次 stage
PALETTE_ORDER = ("yellow", "blue", "red")

# ---------- HUD ----------
SCORE_Y = 44
DIGIT_GAP = 1
HINT_Y = 460
GAMEOVER_IMG_Y = 140
# 结算面板（实心底板）几何：覆盖 SCORE 与 BEST 两行
PANEL_X, PANEL_Y = 44, 196
PANEL_W, PANEL_H = 200, 148
PANEL_FILL = (0xDE, 0xD8, 0x95)     # 与地面同色系，呼应素材
PANEL_BORDER = 3
SCORE_PANEL_Y = 210
BEST_PANEL_Y = 284
OVERLAY_ALPHA = 120           # PAUSED 遮罩
GAMEOVER_OVERLAY_ALPHA = 70   # GAMEOVER 遮罩（更淡，保留现场可见）
FONT_SMALL = 16
FONT_LARGE = 20
INK = (0x54, 0x38, 0x47)
PAPER = (255, 255, 255)
MUTE_BADGE_SECONDS = 1.5

# ---------- 音频 ----------
AUDIO_CHANNELS = 8
SFX_NAMES = ("wing", "point", "hit", "die", "swoosh")
SFX_PRIORITY_GAP_MS = 200     # hit 与 die 最小间隔

# ---------- 行为开关 ----------
PAUSE_ON_FOCUS_LOST = True

# ---------- 退出码 ----------
EXIT_OK = 0
EXIT_ASSET_ERROR = 2
EXIT_DISPLAY_ERROR = 3
