# My Diary - Premium Personal Journal Application

A sophisticated, AI-powered personal diary application built with Flask, featuring advanced wellness tracking, rich text editing, comprehensive data management, and integrated monetization.

## 🚀 Premium Features

### 🤖 AI-Powered Intelligence
- **Smart Writing Prompts**: Get personalized journaling suggestions based on your mood, tags, and categories
- **Sentiment Analysis**: Analyze emotional tone and patterns in your entries
- **Wellness Insights**: AI-generated emotional wellness recommendations based on your journal history

### 📝 Rich Text Editor
- **Quill.js Integration**: Professional WYSIWYG editor with formatting tools
- **Auto-save**: Drafts automatically saved to browser storage
- **Rich Content**: Support for headers, lists, links, images, and more

### 🔍 Advanced Search & Filtering
- **Full-text Search**: Search across titles and content
- **Multi-dimensional Filters**: Filter by mood, category, tags, favorites
- **Smart Pagination**: Configurable entries per page (5, 10, 20)

### 📊 Data Visualization & Analytics
- **Mood Tracking**: Visual mood distribution charts
- **Wellness Dashboard**: Comprehensive emotional health insights
- **Entry Statistics**: Track writing patterns and frequency

### 🏷️ Organization System
- **Categories**: Organize entries into Personal, Work, Family, Health, Travel, Hobbies, Goals, Gratitude, Reflection, Dreams, and Other
- **Tag System**: Flexible tagging for detailed organization
- **Favorites**: Mark important entries for quick access

### 📤 Export Capabilities
- **Multiple Formats**: Export to JSON, CSV, TXT, PDF, and Markdown
- **Rich Data**: Complete metadata including timestamps, moods, and tags
- **Professional PDF**: Formatted PDF exports with proper styling

### 💰 Monetization Integration
- **Google AdSense**: Fully integrated ad management
- **Strategic Ad Placement**: Sidebar and bottom-of-page ads
- **Premium Features Promotion**: Built-in upgrade prompts
- **Revenue Optimization**: Multiple ad formats for better CTR

### 🔐 Security & Privacy
- **Password Reset**: Secure email-based password recovery
- **User Isolation**: Complete data separation between users
- **CSRF Protection**: Comprehensive security measures

### 🎨 Modern UI/UX
- **Gradient Design**: Beautiful gradient backgrounds and animations
- **Dark/Light Themes**: Customizable interface themes
- **Responsive Design**: Mobile-friendly interface
- **Micro-interactions**: Hover effects and smooth transitions
- **Bootstrap Icons**: Comprehensive icon system

## 🛠️ Technology Stack

### Backend
- **Flask 3.0.3**: Modern Python web framework
- **SQLAlchemy**: Powerful ORM with SQLite/PostgreSQL support
- **Flask-Login**: Secure session management
- **Flask-WTF**: CSRF protection and form validation
- **Google Generative AI**: Gemini API integration

### Frontend
- **Bootstrap 5.3.3**: Modern responsive framework
- **Quill.js**: Rich text editor
- **Bootstrap Icons**: Comprehensive icon library
- **Custom CSS**: Gradient designs and animations

### Monetization
- **Google AdSense**: Revenue generation
- **Responsive Ads**: Multiple ad formats
- **Strategic Placement**: Optimized user experience

### Additional Libraries
- **ReportLab**: PDF generation
- **Markdown**: Markdown processing
- **Plotly**: Data visualization
- **Pandas**: Data analysis
- **Werkzeug**: Security utilities

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd my-diary
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   flask run  # Database will be created automatically
   ```

## ⚙️ Configuration

### Required Environment Variables
```env
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///app.db
GEMINI_API_KEY=your-gemini-api-key
```

### Optional Email Configuration
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### AdSense Configuration
```env
ADSENSE_PUBLISHER_ID=ca-pub-2396098605485959
```

### ads.txt File
The application includes an `ads.txt` file for AdSense verification:
- **Location**: `/static/ads.txt`
- **Route**: Served at `/ads.txt`
- **Content**: Publisher verification and authorization
- **Purpose**: Prevents unauthorized ad inventory

## 🎯 Usage

### Getting Started
1. Register for a new account
2. Create your first journal entry
3. Explore AI-powered features
4. Set up your preferences in Settings

### Advanced Features
- **AI Suggestions**: Click "Get AI Suggestions" while writing
- **Sentiment Analysis**: Analyze emotional tone of your entries
- **Wellness Insights**: Visit the Wellness dashboard for personalized insights
- **Export Data**: Use the Export menu to download your journal

## 💰 Monetization Setup

### AdSense Integration
The application comes pre-configured with Google AdSense integration:

1. **Ad Units**:
   - Sidebar ad (300x250 rectangle)
   - Bottom-of-page ad (responsive auto)

2. **Placement Strategy**:
   - Dashboard: Sidebar + bottom ads
   - Other pages: Bottom ads only
   - Authenticated users only (better user experience)

3. **Revenue Optimization**:
   - Responsive ad formats
   - Strategic placement without disrupting UX
   - Premium feature prompts for upselling

4. **Verification Files**:
   - `ads.txt` file for publisher verification
   - Meta tags for AdSense account linking
   - Proper MIME types and headers

### Customization
- Update `ADSENSE_PUBLISHER_ID` in `.env`
- Modify ad slots in templates
- Adjust placement strategy as needed

## 📱 Features Overview

### Dashboard
- Unified view of all entries
- Advanced filtering and search
- Quick actions for editing and favoriting
- Pagination for large datasets
- Integrated sidebar ads

### Entry Management
- Rich text editing with formatting
- Mood and category tracking
- Tag-based organization
- Auto-save functionality

### Wellness Analytics
- Mood distribution charts
- Emotional pattern analysis
- Personalized wellness recommendations
- Entry statistics

### Data Export
- Multiple format support
- Complete metadata preservation
- Professional formatting

## 🔒 Security Features

- **Password Hashing**: Secure password storage
- **CSRF Protection**: Form validation
- **Session Management**: Secure user sessions
- **Input Validation**: Comprehensive input sanitization
- **Email Verification**: Secure password reset

## 🚀 Deployment

### Production Setup
1. Set `FLASK_ENV=production`
2. Configure PostgreSQL database
3. Set up proper email service
4. Configure reverse proxy (nginx)
5. Set up SSL certificates
6. Update AdSense settings for production domain

### Environment Variables for Production
```env
FLASK_ENV=production
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=production-secret-key
ADSENSE_PUBLISHER_ID=your-production-adsense-id
```

## 📈 Monetization Strategy

### Revenue Streams
1. **Display Advertising**: Google AdSense integration
2. **Premium Features**: Future subscription tiers
3. **Data Export**: Advanced export formats for premium users

### Ad Performance Tips
- Monitor AdSense dashboard
- A/B test ad placements
- Optimize for mobile view
- Balance user experience vs. revenue

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:
- Check the documentation
- Review existing issues
- Create a new issue with detailed information

## 🎉 Premium Experience

This application provides a comprehensive journaling experience with:
- Professional UI/UX design
- AI-powered insights
- Advanced organization features
- Multiple export options
- Robust security measures
- Mobile-responsive design
- **Integrated monetization**
- Revenue generation capabilities

Enjoy your premium journaling experience with built-in monetization! 📚✨💰
