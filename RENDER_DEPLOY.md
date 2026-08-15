# Love Quiz - Deployment to Render

This app is designed to be easily deployable on the Render Free Tier.

## Steps to Deploy

1. **Push your code to GitHub:**
   - Initialize a git repository in this folder.
   - Commit all files.
   - Push to a new GitHub repository.

2. **Create a new Web Service on Render:**
   - Go to [render.com](https://render.com) and log in.
   - Click "New +" and select "Web Service".
   - Connect your GitHub account and select your repository.

3. **Configure the Web Service:**
   - **Name:** `love-quiz` (or whatever you prefer)
   - **Language:** `Python 3`
   - **Branch:** `main` (or `master`)
   - **Root Directory:** (leave blank)
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port 10000`

4. **Advanced settings (Optional but recommended):**
   - Ensure the instance type is set to **Free**.
   - No environment variables are strictly needed since SQLite will create the file on the local disk. *Note that on Render's free tier, the disk is ephemeral and the SQLite database will be reset if the server restarts. Since this is a one-off party game for a few hours, this is usually perfectly fine as long as you don't redeploy during the event. If you need persistence across restarts, Render offers a "Disk" feature (which costs a few dollars a month).*

5. **Deploy:**
   - Click **Create Web Service**.
   - Wait a few minutes for Render to build and deploy your app.
   - Your app will be live at the provided URL (e.g., `https://love-quiz.onrender.com`).

## Live Event Management
- Open the leaderboard on a big screen/projector: `https://your-url.onrender.com/leaderboard`
- The host can monitor progress at: `https://your-url.onrender.com/host-xyz123`
- Share the main URL via a QR Code for the guests.
