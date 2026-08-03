# 🌐 100% FREE TELEGRAM BOT HOSTING GUIDE

Follow these exact steps to host your Swiggy Buzz Telegram Bot **100% FREE** 24/7 online!

---

## 🛠️ Step 1: Create Free MongoDB Atlas Cloud Database (2 Mins)

Since free cloud hosting platforms reset local files on restart, we will use a **100% Free MongoDB Atlas Database** (512MB free forever).

1. Go to [MongoDB Atlas Free Signup](https://www.mongodb.com/cloud/atlas/register).
2. Create a free account and choose **M0 Free Cluster**.
3. Under **Database Access**, create a database username & password (e.g., user: `swiggybot`, password: `YourPassword123`).
4. Under **Network Access**, click **Add IP Address** -> Select **Allow Access from Anywhere (`0.0.0.0/0`)**.
5. Click **Connect** -> **Drivers** -> Copy your Connection String:
   ```text
   mongodb+srv://swiggybot:YourPassword123@cluster0.mongodb.net/?retryWrites=true&w=majority
   ```

---

## 🚀 Step 2: Host 100% Free on Render.com (Recommended)

Render gives free computing to run your Python bot 24/7!

1. **Upload your code to GitHub**:
   - Create a GitHub account at [github.com](https://github.com).
   - Create a new repository (e.g. `swiggy-buzz-bot`) and upload all files from `swiggy bot` folder (`bot.py`, `database.py`, `requirements.txt`, etc.).

2. **Deploy on Render**:
   - Go to [render.com](https://render.com) and Sign In with GitHub.
   - Click **New +** (top right) -> Select **Background Worker** (or **Web Service**).
   - Select your `swiggy-buzz-bot` GitHub repository.
   - Set the settings:
     - **Name**: `swiggy-buzz-bot`
     - **Runtime**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python bot.py`
     - **Instance Type**: `Free`
   - Scroll down to **Environment Variables** and add:
     - `BOT_TOKEN` = `8828239744:AAHKaccXHIZDhydfk9Xws6sJxGg5CJCuZGU`
     - `ADMIN_IDS` = `YOUR_TELEGRAM_USER_ID`
     - `MONGO_URI` = `mongodb+srv://swiggybot:YourPassword123@cluster0.mongodb.net/?retryWrites=true&w=majority`
   - Click **Create Background Worker**.

🎉 **Done! Render will deploy your bot and run it 24/7 online for FREE!**

---

## ⚡ Alternative Option: Host Free on Koyeb.com

1. Sign up at [koyeb.com](https://www.koyeb.com).
2. Click **Create App** -> Select **GitHub**.
3. Pick your repository.
4. Set Environment Variables (`BOT_TOKEN`, `ADMIN_IDS`, `MONGO_URI`).
5. Click **Deploy**. Koyeb will run your bot for free!
