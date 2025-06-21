
import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import re
from typing import List, Dict
import pandas as pd

# Set page config
st.set_page_config(
    page_title="AI Tutorial Assistant",
    page_icon="🤖",
    layout="wide"
)

class YouTubeTutorialFinder:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
    
    def extract_topic_from_query(self, user_query: str) -> str:
        """Extract learning topic from natural language query"""
        query_lower = user_query.lower()
        
        patterns_to_remove = [
            r"can you find.*?for\s+",
            r"i want to learn\s+",
            r"teach me\s+",
            r"show me\s+",
            r"find.*?tutorial.*?for\s+",
            r"best.*?tutorial.*?for\s+",
            r"good.*?video.*?for\s+",
            r"help me with\s+",
            r"how to\s+",
            r"learn\s+",
            r"tutorial.*?on\s+",
            r"course.*?on\s+",
            r"video.*?about\s+",
            r"please\s+",
            r"could you\s+",
            r"would you\s+",
        ]
        
        cleaned_query = query_lower
        for pattern in patterns_to_remove:
            cleaned_query = re.sub(pattern, "", cleaned_query)
        
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
        cleaned_query = re.sub(r'^(a|an|the|some|any)\s+', '', cleaned_query)
        
        return cleaned_query if cleaned_query else user_query

    def search_videos(self, query: str, language: str = "en", max_results: int = 20) -> List[Dict]:
        """Search for videos using YouTube Data API"""
        search_url = f"{self.base_url}/search"
        enhanced_query = f"{query} tutorial complete course guide"
        
        params = {
            'part': 'snippet',
            'q': enhanced_query,
            'type': 'video',
            'videoDuration': 'medium',
            'videoDefinition': 'high',
            'relevanceLanguage': language,
            'order': 'relevance',
            'maxResults': max_results,
            'key': self.api_key
        }
        
        try:
            response = requests.get(search_url, params=params)
            response.raise_for_status()
            return response.json().get('items', [])
        except requests.exceptions.RequestException as e:
            st.error(f"Error searching videos: {e}")
            return []
    
    def get_video_details(self, video_ids: List[str]) -> Dict:
        """Get detailed statistics for videos"""
        if not video_ids:
            return {}
            
        details_url = f"{self.base_url}/videos"
        params = {
            'part': 'statistics,contentDetails,snippet',
            'id': ','.join(video_ids),
            'key': self.api_key
        }
        
        try:
            response = requests.get(details_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            video_details = {}
            for item in data.get('items', []):
                video_details[item['id']] = item
            
            return video_details
        except requests.exceptions.RequestException as e:
            st.error(f"Error getting video details: {e}")
            return {}
    
    def parse_duration(self, duration: str) -> int:
        """Parse ISO 8601 duration to seconds"""
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration)
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    def calculate_quality_score(self, video_data: Dict) -> float:
        """Calculate quality score based on various metrics"""
        stats = video_data.get('statistics', {})
        
        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        
        duration_str = video_data.get('contentDetails', {}).get('duration', 'PT0S')
        duration_seconds = self.parse_duration(duration_str)
        duration_minutes = duration_seconds / 60
        
        engagement_rate = (likes + comments) / max(views, 1) * 100
        
        if 10 <= duration_minutes <= 60:
            duration_score = 1.0
        elif 5 <= duration_minutes < 10:
            duration_score = 0.8
        elif 60 < duration_minutes <= 120:
            duration_score = 0.9
        else:
            duration_score = 0.6
        
        quality_score = (
            (views / 1000) * 0.3 +
            engagement_rate * 10 * 0.4 +
            duration_score * 100 * 0.3
        )
        
        return quality_score
    
    def find_best_tutorials(self, user_query: str, language: str = "en", top_n: int = 5) -> List[Dict]:
        """Find and rank the best tutorials from natural language query"""
        topic = self.extract_topic_from_query(user_query)
        search_results = self.search_videos(topic, language)
        
        if not search_results:
            return []
        
        video_ids = [item['id']['videoId'] for item in search_results]
        video_details = self.get_video_details(video_ids)
        
        ranked_videos = []
        for item in search_results:
            video_id = item['id']['videoId']
            if video_id in video_details:
                details = video_details[video_id]
                quality_score = self.calculate_quality_score(details)
                
                video_info = {
                    'video_id': video_id,
                    'title': item['snippet']['title'],
                    'channel': item['snippet']['channelTitle'],
                    'description': item['snippet']['description'][:200] + "...",
                    'thumbnail': item['snippet']['thumbnails']['high']['url'],
                    'published': item['snippet']['publishedAt'],
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'views': int(details['statistics'].get('viewCount', 0)),
                    'likes': int(details['statistics'].get('likeCount', 0)),
                    'comments': int(details['statistics'].get('commentCount', 0)),
                    'duration': details['contentDetails'].get('duration', 'PT0S'),
                    'quality_score': quality_score,
                    'extracted_topic': topic
                }
                
                ranked_videos.append(video_info)
        
        ranked_videos.sort(key=lambda x: x['quality_score'], reverse=True)
        return ranked_videos[:top_n]

class RoadmapGenerator:
    @staticmethod
    def generate_roadmap(topic: str, skill_level: str) -> List[Dict]:
        """Generate a learning roadmap for a given topic"""
        roadmaps = {
            "python": {
                "beginner": [
                    {"step": 1, "title": "Python Basics & Syntax", "duration": "1-2 weeks", "description": "Variables, data types, operators, and basic syntax"},
                    {"step": 2, "title": "Control Structures", "duration": "1 week", "description": "If statements, loops (for, while), conditional logic"},
                    {"step": 3, "title": "Functions & Modules", "duration": "1-2 weeks", "description": "Creating functions, parameters, return values, importing modules"},
                    {"step": 4, "title": "Data Structures", "duration": "2 weeks", "description": "Lists, dictionaries, tuples, sets - manipulation and methods"},
                    {"step": 5, "title": "File Handling & Error Handling", "duration": "1 week", "description": "Reading/writing files, exception handling with try/except"},
                    {"step": 6, "title": "Object-Oriented Programming", "duration": "2 weeks", "description": "Classes, objects, inheritance, encapsulation"},
                    {"step": 7, "title": "Libraries & APIs", "duration": "1-2 weeks", "description": "Working with external libraries, API calls, JSON handling"}
                ],
                "intermediate": [
                    {"step": 1, "title": "Advanced Data Structures", "duration": "1 week", "description": "Comprehensions, generators, decorators"},
                    {"step": 2, "title": "Web Development", "duration": "3-4 weeks", "description": "Flask/Django basics, HTML templates, routing"},
                    {"step": 3, "title": "Database Integration", "duration": "2 weeks", "description": "SQLite, PostgreSQL, ORM concepts"},
                    {"step": 4, "title": "Testing & Debugging", "duration": "1 week", "description": "Unit testing, debugging techniques, logging"},
                    {"step": 5, "title": "Data Analysis", "duration": "2-3 weeks", "description": "Pandas, NumPy, data manipulation and visualization"},
                    {"step": 6, "title": "API Development", "duration": "2 weeks", "description": "RESTful APIs, FastAPI, authentication"},
                    {"step": 7, "title": "Deployment", "duration": "1 week", "description": "Heroku, Docker basics, environment management"}
                ]
            },
            "javascript": {
                "beginner": [
                    {"step": 1, "title": "JavaScript Fundamentals", "duration": "1-2 weeks", "description": "Variables, data types, operators, basic syntax"},
                    {"step": 2, "title": "DOM Manipulation", "duration": "1-2 weeks", "description": "Selecting elements, event handling, dynamic content"},
                    {"step": 3, "title": "Functions & Scope", "duration": "1 week", "description": "Function declarations, arrow functions, scope concepts"},
                    {"step": 4, "title": "Arrays & Objects", "duration": "1-2 weeks", "description": "Array methods, object manipulation, JSON"},
                    {"step": 5, "title": "Asynchronous JavaScript", "duration": "2 weeks", "description": "Promises, async/await, fetch API"},
                    {"step": 6, "title": "ES6+ Features", "duration": "1 week", "description": "Let/const, template literals, destructuring, modules"},
                    {"step": 7, "title": "Basic Projects", "duration": "2 weeks", "description": "Todo app, calculator, simple games"}
                ],
                "intermediate": [
                    {"step": 1, "title": "Modern JavaScript Frameworks", "duration": "3-4 weeks", "description": "React.js or Vue.js fundamentals"},
                    {"step": 2, "title": "State Management", "duration": "2 weeks", "description": "Redux, Context API, component state"},
                    {"step": 3, "title": "API Integration", "duration": "1-2 weeks", "description": "REST APIs, GraphQL, authentication"},
                    {"step": 4, "title": "Build Tools", "duration": "1 week", "description": "Webpack, Vite, npm/yarn package management"},
                    {"step": 5, "title": "Testing", "duration": "1-2 weeks", "description": "Jest, React Testing Library, unit testing"},
                    {"step": 6, "title": "Performance Optimization", "duration": "1 week", "description": "Code splitting, lazy loading, memoization"},
                    {"step": 7, "title": "Full-Stack Project", "duration": "3-4 weeks", "description": "Complete web application with backend integration"}
                ]
            },
            "machine learning": {
                "beginner": [
                    {"step": 1, "title": "Math Foundations", "duration": "2-3 weeks", "description": "Linear algebra, statistics, calculus basics"},
                    {"step": 2, "title": "Python for ML", "duration": "2 weeks", "description": "NumPy, Pandas, Matplotlib fundamentals"},
                    {"step": 3, "title": "Data Preprocessing", "duration": "1-2 weeks", "description": "Cleaning data, handling missing values, feature scaling"},
                    {"step": 4, "title": "Supervised Learning", "duration": "3 weeks", "description": "Linear regression, logistic regression, decision trees"},
                    {"step": 5, "title": "Model Evaluation", "duration": "1 week", "description": "Cross-validation, metrics, overfitting/underfitting"},
                    {"step": 6, "title": "Unsupervised Learning", "duration": "2 weeks", "description": "Clustering, dimensionality reduction, PCA"},
                    {"step": 7, "title": "First ML Project", "duration": "2 weeks", "description": "End-to-end project with real dataset"}
                ],
                "intermediate": [
                    {"step": 1, "title": "Advanced Algorithms", "duration": "3 weeks", "description": "Random Forest, SVM, ensemble methods"},
                    {"step": 2, "title": "Deep Learning Basics", "duration": "4 weeks", "description": "Neural networks, TensorFlow/PyTorch introduction"},
                    {"step": 3, "title": "Computer Vision", "duration": "3 weeks", "description": "CNN, image processing, OpenCV"},
                    {"step": 4, "title": "Natural Language Processing", "duration": "3 weeks", "description": "Text preprocessing, sentiment analysis, word embeddings"},
                    {"step": 5, "title": "MLOps Fundamentals", "duration": "2 weeks", "description": "Model deployment, monitoring, version control"},
                    {"step": 6, "title": "Advanced Projects", "duration": "4-5 weeks", "description": "Portfolio projects with real-world applications"},
                    {"step": 7, "title": "Specialization", "duration": "Ongoing", "description": "Choose focus area: CV, NLP, or other domain"}
                ]
            }
        }
        
        # Extract main topic keyword
        topic_lower = topic.lower()
        for key in roadmaps.keys():
            if key in topic_lower:
                return roadmaps[key].get(skill_level, roadmaps[key]["beginner"])
        
        # Generic roadmap if topic not found
        return [
            {"step": 1, "title": "Fundamentals", "duration": "1-2 weeks", "description": f"Learn basic concepts of {topic}"},
            {"step": 2, "title": "Core Concepts", "duration": "2-3 weeks", "description": f"Dive deeper into {topic} principles"},
            {"step": 3, "title": "Practical Application", "duration": "2-3 weeks", "description": f"Build projects using {topic}"},
            {"step": 4, "title": "Advanced Topics", "duration": "3-4 weeks", "description": f"Explore advanced {topic} concepts"},
            {"step": 5, "title": "Specialization", "duration": "Ongoing", "description": f"Focus on specific areas within {topic}"}
        ]

def format_duration(duration_str: str) -> str:
    """Format ISO 8601 duration to readable format"""
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    if not match:
        return "Unknown"
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"

def format_number(num: int) -> str:
    """Format large numbers with K, M suffixes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return str(num)

def main():
    # Custom CSS for better styling - FIXED COLORS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sector-header {
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .chat-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        min-height: 300px;
    }
    .chat-message {
        margin-bottom: 10px;
        padding: 8px;
        border-radius: 5px;
        color: #333 !important;
    }
    .roadmap-step {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: #333 !important;
    }
    .roadmap-step h4 {
        color: #667eea !important;
        margin-bottom: 0.5rem;
    }
    .roadmap-step p {
        color: #555 !important;
        margin-bottom: 0.3rem;
    }
    .tutorial-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .tutorial-card h4 {
        color: #333 !important;
        margin-bottom: 0.5rem;
    }
    .tutorial-card p {
        color: #666 !important;
        margin-bottom: 0.3rem;
    }
    .tutorial-stats {
        color: #007bff !important;
        font-weight: 500;
        margin: 0.5rem 0;
    }
    .tutorial-thumbnail {
        width: 100%;
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }
    .roadmap-text {
        white-space: pre-line;
        line-height: 1.6;
        color: #333 !important;
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
    .stTextInput > div > div > input {
        color: #333 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 AI Tutorial Assistant</h1>
        <p>Your comprehensive learning companion with Chat, Tutorials & Roadmaps</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session states
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "tutorial_results" not in st.session_state:
        st.session_state.tutorial_results = []
    if "current_roadmap" not in st.session_state:
        st.session_state.current_roadmap = []
    if "chat_input_key" not in st.session_state:
        st.session_state.chat_input_key = 0
    
    # API key
    api_key = "AIzaSyAMfLDk0L_I9GC4jp1myPA6QKaoNEyI0cY"
    
    # Create three columns for the sectors
    col1, col2, col3 = st.columns([1, 1, 1])
    
    # SECTOR 1: GENERAL CHAT - FIXED
    with col1:
        st.markdown('<div class="sector-header"><h3>💬 General Chat</h3></div>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown('<div class="chat-container">', unsafe_allow_html=True)
            
            # Display chat messages
            chat_container = st.container()
            with chat_container:
                for message in st.session_state.chat_messages[-8:]:  # Show last 8 messages
                    if message["role"] == "user":
                        st.markdown(f'<div class="chat-message"><strong>You:</strong> {message["content"]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="chat-message"><strong>Assistant:</strong> {message["content"]}</div>', unsafe_allow_html=True)
            
            # Chat input - FIXED with key management
            chat_input = st.text_input(
                "Ask me anything...", 
                key=f"chat_input_{st.session_state.chat_input_key}", 
                placeholder="Type your question here..."
            )
            
            col1a, col1b = st.columns([3, 1])
            with col1b:
                send_clicked = st.button("Send", key=f"chat_send_{st.session_state.chat_input_key}")
            
            if send_clicked and chat_input.strip():
                # Add user message
                st.session_state.chat_messages.append({"role": "user", "content": chat_input.strip()})
                
                # Generate response (enhanced responses)
                responses = [
                    "That's a great question! I'm here to help you learn anything you want.",
                    "I understand! Let me know if you need tutorials or learning resources on any topic.",
                    "Interesting topic! Would you like me to find some tutorials or create a roadmap for this?",
                    "I'm designed to help you learn effectively. What specific area would you like to explore?",
                    "Feel free to ask me to find tutorials or create a personalized learning roadmap!",
                    "Great! I can help you find the best learning resources. What's your current skill level?",
                    "That's a wonderful learning goal! Would you like structured tutorials or a step-by-step roadmap?"
                ]
                
                import random
                response = random.choice(responses)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
                
                # Clear input by incrementing key
                st.session_state.chat_input_key += 1
                st.rerun()
            
            # Clear chat button
            if st.button("🗑️ Clear Chat", key="clear_chat"):
                st.session_state.chat_messages = []
                st.session_state.chat_input_key += 1
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # SECTOR 2: VIDEO TUTORIALS - FIXED
    with col2:
        st.markdown('<div class="sector-header"><h3>🎥 Video Tutorials</h3></div>', unsafe_allow_html=True)
        
        # Tutorial search input
        tutorial_query = st.text_input("What do you want to learn?", key="tutorial_search", placeholder="e.g., Python, React, Machine Learning...")
        
        # Language and results settings
        col2a, col2b = st.columns(2)
        with col2a:
            language_options = {
                "English": "en", "Spanish": "es", "French": "fr", "German": "de"
            }
            selected_language = st.selectbox("Language", list(language_options.keys()), key="tutorial_lang")
        
        with col2b:
            num_results = st.selectbox("Results", [3, 5, 8], index=1, key="tutorial_num")
        
        if st.button("🔍 Find Tutorials", key="find_tutorials") and tutorial_query:
            with st.spinner("Searching for tutorials..."):
                finder = YouTubeTutorialFinder(api_key)
                tutorials = finder.find_best_tutorials(
                    tutorial_query,
                    language_options[selected_language],
                    num_results
                )
                st.session_state.tutorial_results = tutorials
        
        # Display tutorial results - FIXED STYLING
        if st.session_state.tutorial_results:
            st.markdown("### 📚 Found Tutorials:")
            for i, tutorial in enumerate(st.session_state.tutorial_results, 1):
                st.markdown(f"""
                <div class="tutorial-card">
                    <img src="{tutorial['thumbnail']}" class="tutorial-thumbnail" alt="Video thumbnail">
                    <h4>#{i} {tutorial['title']}</h4>
                    <p><em>by {tutorial['channel']}</em></p>
                    <div class="tutorial-stats">
                        👀 {format_number(tutorial['views'])} views • 
                        👍 {format_number(tutorial['likes'])} likes • 
                        ⏱️ {format_duration(tutorial['duration'])}
                    </div>
                    <p><a href="{tutorial['url']}" target="_blank" style="color: #007bff; text-decoration: none;">🔗 Watch Tutorial</a></p>
                </div>
                """, unsafe_allow_html=True)
    
    # SECTOR 3: LEARNING ROADMAP - FIXED
    with col3:
        st.markdown('<div class="sector-header"><h3>🗺️ Learning Roadmap</h3></div>', unsafe_allow_html=True)
        
        # Roadmap inputs
        roadmap_topic = st.text_input("Topic for roadmap:", key="roadmap_topic", placeholder="e.g., Python, JavaScript, Machine Learning...")
        skill_level = st.selectbox("Your skill level:", ["beginner", "intermediate", "advanced"], key="roadmap_level")
        
        if st.button("📋 Generate Roadmap", key="generate_roadmap") and roadmap_topic:
            roadmap = RoadmapGenerator.generate_roadmap(roadmap_topic, skill_level)
            st.session_state.current_roadmap = roadmap
        
        # Display roadmap - FIXED STYLING
        if st.session_state.current_roadmap:
            st.markdown("### 🎯 Your Learning Path:")
            
            # Add option to display as text
            show_as_text = st.checkbox("Show as plain text", key="show_text_version")
            
            if show_as_text:
                roadmap_text = f"Learning Roadmap for {roadmap_topic.capitalize()} ({skill_level.capitalize()} level):\n\n"
                for step in st.session_state.current_roadmap:
                    roadmap_text += f"Step {step['step']}: {step['title']}\n"
                    roadmap_text += f"Duration: {step['duration']}\n"
                    roadmap_text += f"Description: {step['description']}\n\n"
                
                st.markdown(f'<div class="roadmap-text">{roadmap_text}</div>', unsafe_allow_html=True)
            else:
                for step in st.session_state.current_roadmap:
                    st.markdown(f"""
                    <div class="roadmap-step">
                        <h4>Step {step['step']}: {step['title']}</h4>
                        <p><strong>Duration:</strong> {step['duration']}</p>
                        <p><strong>Description:</strong> {step['description']}</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 0.9em; margin-top: 2rem;'>
        🤖 <strong>AI Tutorial Assistant</strong> | Chat • Learn • Progress | Made with ❤️ using Streamlit
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
