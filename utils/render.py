import base64
import os
from datetime import datetime
import calendar

class DeerPipeRenderer:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        self.assets_dir = os.path.join(plugin_dir, "assets")

    def _get_image_base64(self, path: str):
        if not os.path.exists(path):
            return ""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    async def render_calendar(self, star, username: str, year: int, month: int, checkin_records: list, preset: str = "1"):
        # checkin_records: list of (date_str, count)
        # date_str: YYYY-MM-DD
        
        # Get assets
        bg_path = os.path.join(self.assets_dir, preset, "1.png")
        check_path = os.path.join(self.assets_dir, preset, "2.png")
        
        bg_base64 = self._get_image_base64(bg_path)
        check_base64 = self._get_image_base64(check_path)
        
        # Prepare data for template
        first_day_weekday, num_days = calendar.monthrange(year, month)
        # calendar.monthrange returns (first_day_weekday, num_days) where 0 is Monday
        # We want Sunday as 0 for the grid usually, or just follow the logic
        start_padding = (first_day_weekday + 1) % 7 # Adjust to Sun=0
        
        days_data = []
        # Padding
        for _ in range(start_padding):
            days_data.append(None)
            
        # Actual days
        checkin_map = {int(r[0].split("-")[-1]): r[1] for r in checkin_records}
        for day in range(1, num_days + 1):
            count = checkin_map.get(day, 0)
            days_data.append({
                "day": day,
                "count": count,
                "checked": count > 0
            })

        # Template
        tmpl = """
        <div class="calendar">
            <div class="calendar-header">{{ year }}-{{ "%02d"|format(month) }} 签到</div>
            <div class="calendar-subheader">{{ username }}</div>
            <div class="weekdays">
                <div>日</div><div>一</div><div>二</div><div>三</div><div>四</div><div>五</div><div>六</div>
            </div>
            <div class="calendar-grid">
                {% for day_info in days %}
                    <div class="calendar-day">
                        {% if day_info %}
                            <img src="data:image/png;base64,{{ bg_base64 }}" class="deer-image">
                            {% if day_info.checked %}
                                <img src="data:image/png;base64,{{ check_base64 }}" class="check-image">
                                {% if day_info.count > 1 %}
                                    <div class="multiple-sign">×{{ day_info.count }}</div>
                                {% endif %}
                            {% endif %}
                            <div class="day-number">{{ day_info.day }}</div>
                        {% endif %}
                    </div>
                {% endfor %}
            </div>
        </div>
        <style>
            html, body { margin: 0; padding: 0; width: fit-content; height: fit-content; background: transparent; }
            body { display: inline-block; }
            .calendar { width: 320px; background: white; padding: 15px; border-radius: 10px; font-family: "Microsoft YaHei", sans-serif; }
            .calendar-header { font-size: 20px; font-weight: bold; margin-bottom: 5px; color: #333; }
            .calendar-subheader { font-size: 14px; color: #666; margin-bottom: 15px; }
            .weekdays { display: grid; grid-template-columns: repeat(7, 1fr); text-align: center; font-size: 12px; color: #999; margin-bottom: 10px; }
            .calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; }
            .calendar-day { position: relative; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
            .deer-image { width: 100%; height: 100%; object-fit: cover; border-radius: 4px; }
            .check-image { position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0.8; }
            .day-number { position: absolute; bottom: 2px; left: 4px; font-size: 12px; font-weight: bold; color: #333; text-shadow: 1px 1px 2px white; }
            .multiple-sign { position: absolute; top: 2px; right: 2px; font-size: 10px; font-weight: bold; color: #ff4d4f; background: rgba(255,255,255,0.8); border-radius: 2px; padding: 0 2px; }
        </style>
        """
        
        render_data = {
            "year": year,
            "month": month,
            "username": username,
            "days": days_data,
            "bg_base64": bg_base64,
            "check_base64": check_base64
        }
        
        return await star.html_render(tmpl, render_data)

    async def render_leaderboard(self, star, month_name: str, rank_data: list):
        # rank_data: list of Row(username, total_times)
        
        tmpl = """
        <div class="leaderboard">
            <h1>🦌 {{ month_name }} 鹿管排行榜 🦌</h1>
            <div class="list">
                {% for item in rank_data %}
                <div class="item">
                    <span class="rank">{{ loop.index }}</span>
                    {% if loop.index == 1 %}<span class="medal">🥇</span>{% endif %}
                    {% if loop.index == 2 %}<span class="medal">🥈</span>{% endif %}
                    {% if loop.index == 3 %}<span class="medal">🥉</span>{% endif %}
                    <span class="name">{{ item.username }}</span>
                    <span class="count">{{ item.total_times }} 次</span>
                </div>
                {% endfor %}
            </div>
        </div>
        <style>
            html, body { margin: 0; padding: 0; width: fit-content; height: fit-content; background: transparent; }
            body { display: inline-block; }
            .leaderboard { width: 350px; background: #fff; padding: 25px; border-radius: 12px; font-family: "Microsoft YaHei", sans-serif; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            h1 { text-align: center; color: #2c3e50; font-size: 22px; margin-bottom: 25px; }
            .item { display: flex; align-items: center; padding: 12px 10px; border-bottom: 1px solid #eee; }
            .rank { width: 30px; font-weight: bold; color: #95a5a6; font-size: 16px; }
            .medal { font-size: 20px; margin-right: 10px; }
            .name { flex-grow: 1; font-size: 16px; color: #34495e; }
            .count { font-weight: bold; color: #e74c3c; font-size: 16px; }
        </style>
        """
        
        return await star.html_render(tmpl, {"month_name": month_name, "rank_data": rank_data})
