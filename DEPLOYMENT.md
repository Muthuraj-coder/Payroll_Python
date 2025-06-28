# 🚀 Deployment Guide for Flask Payroll Application

## Prerequisites
- GitHub account
- Render account (free tier available)
- Your Flask application code

## Step-by-Step Deployment Process

### 1. Prepare Your Code (✅ Already Done)
Your project is configured with:
- `render.yaml` - Render deployment configuration
- `requirements.txt` - Python dependencies including gunicorn
- `migrate.py` - Database initialization script
- Proper Flask app structure

### 2. Push to GitHub

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit for Render deployment"

# Create GitHub repository and push
git remote add origin https://github.com/yourusername/payroll-python.git
git branch -M main
git push -u origin main
```

### 3. Deploy on Render

#### 3.1 Create Render Account
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Sign up with your GitHub account

#### 3.2 Create Database
1. Click "New +" → "PostgreSQL"
2. Configure:
   - **Name**: `payroll-db`
   - **Plan**: Free
   - **Region**: Choose closest to your users
3. Click "Create Database"
4. **Save the connection string** - you'll need it later

#### 3.3 Create Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Select the `payroll-python` repository
4. Configure the service:

**Basic Settings:**
- **Name**: `payroll-flask-app`
- **Environment**: `Python 3`
- **Region**: Same as database
- **Branch**: `main`

**Build & Deploy:**
- **Build Command**: `pip install -r requirements.txt && python migrate.py`
- **Start Command**: `gunicorn run:app`

**Environment Variables:**
- `DATABASE_URL`: [Use the connection string from your database]
- `SECRET_KEY`: [Generate a secure random key]
- `FLASK_APP`: `run.py`
- `FLASK_ENV`: `production`

5. Click "Create Web Service"

### 4. Monitor Deployment

1. **Watch the build logs** for any errors
2. **Check the deployment status** - should show "Live"
3. **Test your application** using the provided URL

### 5. Post-Deployment Setup

#### 5.1 Access Your Application
- Your app will be available at: `https://payroll-flask-app.onrender.com`
- Admin login: `admin` / `admin123`

#### 5.2 Security Recommendations
1. **Change admin password** immediately after first login
2. **Update SECRET_KEY** in production
3. **Enable HTTPS** (automatic on Render)

### 6. Troubleshooting

#### Common Issues:

**Build Fails:**
- Check `requirements.txt` for missing dependencies
- Verify Python version compatibility
- Check build logs for specific errors

**Database Connection Issues:**
- Verify `DATABASE_URL` is correctly set
- Check database is running and accessible
- Ensure `psycopg2-binary` is in requirements.txt

**App Won't Start:**
- Check `startCommand` in render.yaml
- Verify `run.py` exports the app correctly
- Check application logs for errors

#### Debug Commands:
```bash
# Check local database connection
python migrate.py

# Test local app
python run.py

# Check requirements
pip install -r requirements.txt
```

### 7. Maintenance

#### Updates:
1. Make changes to your code
2. Commit and push to GitHub
3. Render will automatically redeploy

#### Database Backups:
- Render provides automatic backups for paid plans
- For free tier, consider manual exports

#### Monitoring:
- Use Render's built-in logging
- Set up health checks
- Monitor performance metrics

## 🎉 Success!

Your Flask Payroll application is now deployed and accessible online!

**Default Admin Credentials:**
- Username: `admin`
- Password: `admin123`

**Remember to change these credentials after first login!**

## Support

If you encounter issues:
1. Check Render's documentation
2. Review build and runtime logs
3. Verify all environment variables are set correctly
4. Test locally before deploying 