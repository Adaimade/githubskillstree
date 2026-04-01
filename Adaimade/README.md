# 🌳 GitHub Skill Tree

> *自動分析你的 GitHub 技能，生成技能樹卡片*

在你的 GitHub Profile README 中加入這一行：

```markdown
![Skill Tree](https://github-skillstree.zeabur.app/api/skill-tree?username=你的帳號)
```

就會顯示這張卡片（自動分析，無需設定）：

![Skill Tree](https://github-skillstree.zeabur.app/api/skill-tree?username=Adaimade)

---

## 📊 卡片內容

| 區塊 | 說明 |
|------|------|
| **DETECTED SKILLS** | 從你的倉庫自動偵測到的技能，含熟練度點數 |
| **RECOMMENDED NEXT** | AI 根據你的技能推薦下一步學習方向 |
| **JOB MATCH** | 你的技能組合對應的職位和匹配度、薪資範圍 |
| **LANGUAGES** | 你使用最多的程式語言 |

---

## 🚀 部署方式

本專案架構與 [Project_SystemAlert](https://github.com/Adaimade/Project_SystemAlert) 相同：

1. **Fork 這個 repo**
2. **部署到 Zeabur**（點一下自動部署）
3. 設定環境變數 `GITHUB_TOKEN`（可選，提升 API 速率）
4. 把你的網址貼到 README：
   ```markdown
   ![Skill Tree](https://your-app.zeabur.app/api/skill-tree?username=你的帳號)
   ```

---

## 🛠️ 本地測試

```bash
pip install flask requests
python app.py
# 打開 http://localhost:5000/api/skill-tree?username=你的帳號
```

---

Made with 🖤 by **ADAIMADE**
