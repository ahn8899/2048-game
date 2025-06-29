import os
import random
import sqlite3
import requests
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# ========== 目录/数据库路径自动适配 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'scores.db')

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
app.secret_key = 'your-secret-key-here'

# ===== 多语言配置 =====
LANGUAGES = {
    'zh': {
        'title': '2048游戏',
        'welcome': '欢迎来到2048游戏！',
        'start_game': '开始游戏',
        'instructions': '使用方向键或WASD键移动方块，合并相同数字到达2048！',
        'language': '语言',
        'game_title': '2048',
        'score': '分数',
        'best': '最佳',
        'restart': '重新开始',
        'game_over': '游戏结束！',
        'you_win': '恭喜你赢了！',
        'continue': '继续游戏',
        'try_again': '再试一次',
        'back_to_menu': '返回主菜单',
        'controls': '控制方式：方向键/WASD/滑动屏幕',
        'leaderboard': '排行榜',
        'settings': '设置',
        'theme': '主题',
        'light': '亮色',
        'dark': '暗色',
        'save': '保存',
        'coming_soon': '敬请期待'
    },
    'en': {
        'title': '2048 Game',
        'welcome': 'Welcome to 2048 Game!',
        'start_game': 'Start Game',
        'instructions': 'Use arrow keys or WASD to move tiles and merge same numbers to reach 2048!',
        'language': 'Language',
        'game_title': '2048',
        'score': 'Score',
        'best': 'Best',
        'restart': 'Restart',
        'game_over': 'Game Over!',
        'you_win': 'You Win!',
        'continue': 'Continue',
        'try_again': 'Try Again',
        'back_to_menu': 'Back to Menu',
        'controls': 'Controls: Arrow keys/WASD/Swipe',
        'leaderboard': 'Leaderboard',
        'settings': 'Settings',
        'theme': 'Theme',
        'light': 'Light',
        'dark': 'Dark',
        'save': 'Save',
        'coming_soon': 'Coming soon'
    },
    'ko': {
        'title': '2048 게임',
        'welcome': '2048 게임에 오신 것을 환영합니다!',
        'start_game': '게임 시작',
        'instructions': '방향키, WASD, 또는 스와이프로 타일을 이동하여 2048을 만들어보세요!',
        'language': '언어',
        'game_title': '2048',
        'score': '점수',
        'best': '최고',
        'restart': '다시 시작',
        'game_over': '게임 오버!',
        'you_win': '승리!',
        'continue': '계속하기',
        'try_again': '다시 시도',
        'back_to_menu': '메인 메뉴',
        'controls': '조작법: 방향키/WASD/스와이프',
        'leaderboard': '리더보드',
        'settings': '설정',
        'theme': '테마',
        'light': '라이트',
        'dark': '다크',
        'save': '저장',
        'coming_soon': '곧 공개'
    },
    'ja': {
        'title': '2048ゲーム',
        'welcome': '2048ゲームへようこそ！',
        'start_game': 'ゲーム開始',
        'instructions': '矢印キーやWASD、スワイプで同じ数字を合成して2048を目指そう！',
        'language': '言語',
        'game_title': '2048',
        'score': 'スコア',
        'best': 'ベスト',
        'restart': '再スタート',
        'game_over': 'ゲームオーバー！',
        'you_win': 'クリア！',
        'continue': '続ける',
        'try_again': 'もう一度',
        'back_to_menu': 'メニューに戻る',
        'controls': '操作方法：矢印/WASD/スワイプ',
        'leaderboard': 'ランキング',
        'settings': '設定',
        'theme': 'テーマ',
        'light': 'ライト',
        'dark': 'ダーク',
        'save': '保存',
        'coming_soon': '近日公開'
    }
    # 可继续扩展更多语言
}

LANG_COUNTRY_MAP = {
    'KR': 'ko', 'CN': 'zh', 'TW': 'zh', 'HK': 'zh', 'MO': 'zh', 'JP': 'ja',
    'US': 'en', 'GB': 'en', 'AU': 'en', 'CA': 'en'
}

def guess_lang_by_ip(ip):
    try:
        resp = requests.get(f'https://ipinfo.io/{ip}/json', timeout=2)
        data = resp.json()
        country = data.get('country')
        if country and country in LANG_COUNTRY_MAP:
            return LANG_COUNTRY_MAP[country]
    except Exception:
        pass
    return None

def guess_lang_from_header():
    lang = request.accept_languages.best_match(list(LANGUAGES.keys()))
    return lang or 'en'

# ===== SQLite排行榜实现 =====
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS scores
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT, score INTEGER, date TEXT DEFAULT CURRENT_TIMESTAMP)''')
    conn.close()

def save_score(user, score):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO scores (user, score) VALUES (?, ?)", (user, score))
    conn.commit()
    conn.close()

def load_top_scores(limit=20):  # 默认取前20名
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT user, score, date FROM scores ORDER BY score DESC, date ASC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

init_db()

# ===== 游戏核心 =====
class Game2048:
    def __init__(self):
        self.size = 4
        self.board = [[0 for _ in range(self.size)] for _ in range(self.size)]
        self.score = 0
        self.moved = False
        self.add_random_tile()
        self.add_random_tile()

    def add_random_tile(self):
        empty_cells = [(i, j) for i in range(self.size) for j in range(self.size) if self.board[i][j] == 0]
        if empty_cells:
            i, j = random.choice(empty_cells)
            self.board[i][j] = 2 if random.random() < 0.9 else 4

    def move_left(self):
        self.moved = False
        for i in range(self.size):
            row = [val for val in self.board[i] if val != 0]
            j = 0
            while j < len(row) - 1:
                if row[j] == row[j + 1]:
                    row[j] *= 2
                    self.score += row[j]
                    del row[j + 1]
                    self.moved = True
                j += 1
            row += [0] * (self.size - len(row))
            if self.board[i] != row:
                self.moved = True
            self.board[i] = row

    def move_right(self):
        for i in range(self.size):
            self.board[i] = self.board[i][::-1]
        self.move_left()
        for i in range(self.size):
            self.board[i] = self.board[i][::-1]

    def move_up(self):
        self.transpose()
        self.move_left()
        self.transpose()

    def move_down(self):
        self.transpose()
        self.move_right()
        self.transpose()

    def transpose(self):
        self.board = [[self.board[j][i] for j in range(self.size)] for i in range(self.size)]

    def can_move(self):
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] == 0:
                    return True
        for i in range(self.size):
            for j in range(self.size):
                current = self.board[i][j]
                if j < self.size - 1 and current == self.board[i][j + 1]:
                    return True
                if i < self.size - 1 and current == self.board[i + 1][j]:
                    return True
        return False

    def has_won(self):
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] >= 2048:
                    return True
        return False

    def get_state(self):
        return {
            'board': self.board,
            'score': self.score,
            'game_over': not self.can_move(),
            'won': self.has_won()
        }

# ====== 路由 ======
@app.route('/')
def index():
    lang = request.args.get('lang')
    if not lang:
        lang = session.get('lang')
    if not lang:
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        lang = guess_lang_by_ip(user_ip)
    if not lang:
        lang = guess_lang_from_header()
    if lang not in LANGUAGES:
        lang = 'zh'
    session['lang'] = lang
    return render_template('index.html', lang=lang, text=LANGUAGES[lang], languages=LANGUAGES)

@app.route('/settings')
def settings():
    lang = session.get('lang', 'zh')
    return render_template('settings.html', lang=lang, text=LANGUAGES[lang], languages=LANGUAGES)

@app.route('/set_language', methods=['POST'])
def set_language():
    lang = request.form.get('lang')
    if lang in LANGUAGES:
        session['lang'] = lang
    ref = request.referrer or url_for('index')
    return redirect(f'{ref.split("?")[0]}?lang={lang}')

@app.route('/game')
def game():
    lang = session.get('lang', 'zh')
    game = Game2048()
    session['game_state'] = {
        'board': game.board,
        'score': game.score
    }
    session['best_score'] = session.get('best_score', 0)
    return render_template('game.html', lang=lang, text=LANGUAGES[lang], languages=LANGUAGES)

@app.route('/leaderboard')
def leaderboard():
    lang = session.get('lang', 'zh')
    return render_template('leaderboard.html', lang=lang, text=LANGUAGES[lang], languages=LANGUAGES)

@app.route('/api/game/state')
def get_game_state():
    if 'game_state' not in session:
        game = Game2048()
        session['game_state'] = {
            'board': game.board,
            'score': game.score
        }
    game = Game2048()
    game.board = session['game_state']['board']
    game.score = session['game_state']['score']
    state = game.get_state()
    state['best_score'] = session.get('best_score', 0)
    return jsonify(state)

@app.route('/api/game/move', methods=['POST'])
def move():
    direction = request.json.get('direction')
    if 'game_state' not in session:
        return jsonify({'error': 'No game in progress'})
    game = Game2048()
    game.board = session['game_state']['board']
    game.score = session['game_state']['score']
    if direction == 'left':
        game.move_left()
    elif direction == 'right':
        game.move_right()
    elif direction == 'up':
        game.move_up()
    elif direction == 'down':
        game.move_down()
    if game.moved:
        game.add_random_tile()
    if game.score > session.get('best_score', 0):
        session['best_score'] = game.score
    session['game_state'] = {
        'board': game.board,
        'score': game.score
    }
    state = game.get_state()
    state['best_score'] = session.get('best_score', 0)
    return jsonify(state)

@app.route('/api/game/restart', methods=['POST'])
def restart():
    game = Game2048()
    session['game_state'] = {
        'board': game.board,
        'score': game.score
    }
    state = game.get_state()
    state['best_score'] = session.get('best_score', 0)
    return jsonify(state)

@app.route('/api/leaderboard')
def api_leaderboard():
    scores = load_top_scores(20)
    return jsonify([{'user': s[0], 'score': s[1], 'date': s[2]} for s in scores])

@app.route('/api/submit_score', methods=['POST'])
def submit_score():
    data = request.json
    user = data.get('user', '匿名')
    score = data.get('score', 0)
    try:
        save_score(user, int(score))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ========= 稳定的入口 ==========
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
