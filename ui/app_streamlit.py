"""
Streamlit UI for Fake News Detection Agent
Industrial-standard interface with real-time agent thinking visualization
"""

import streamlit as st
import sys
import time
from pathlib import Path
from datetime import datetime
import difflib
import random
import os
from typing import Optional, Dict, List, Tuple

# ==========================================
# FIX: Set up proper Python path
# ==========================================
# Get the absolute path to the backend directory
BACKEND_PATH = Path(__file__).parent.parent / "backend"
BACKEND_PATH = BACKEND_PATH.resolve()  # Resolve to absolute path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Add paths to sys.path for imports (don't change working directory)
sys.path.insert(0, str(BACKEND_PATH))
sys.path.insert(0, str(PROJECT_ROOT))

# Store original working directory and restore it after imports
ORIGINAL_CWD = os.getcwd()

# Now import backend modules
# Note: IDE may show import errors due to dynamic path setup, but these work at runtime
try:
    from agents.fact_check_agent_adk import FactCheckSequentialAgent  # pyright: ignore[reportMissingImports]
    from agents.image_processing_agent import ImageProcessingAgent  # pyright: ignore[reportMissingImports]
    from memory.manager import MemoryManager  # pyright: ignore[reportMissingImports]
    from config import get_logger  # pyright: ignore[reportMissingImports]
except ImportError as e:
    st.error(f"Import Error: {e}")
    st.error(f"Backend path: {BACKEND_PATH}")
    st.error(f"Backend path exists: {BACKEND_PATH.exists()}")
    st.stop()

logger = get_logger(__name__)

# ==========================================
# Page Configuration
# ==========================================
st.set_page_config(
    page_title="Fake News Detection Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# Custom CSS for Industrial Standard UI
# ==========================================
st.markdown("""
<style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Header styling */
    .header-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    /* Verdict badges */
    .verdict-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.1rem;
        margin: 0.5rem 0;
    }
    
    .verdict-true {
        background-color: #2ecc71;
        color: white;
    }
    
    .verdict-false {
        background-color: #e74c3c;
        color: white;
    }
    
    .verdict-mixed {
        background-color: #f39c12;
        color: white;
    }
    
    /* Info boxes */
    .info-box {
        background-color: #f0f7ff;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
    }
    
    .success-box {
        background-color: #e8f5e9;
        border-left-color: #2ecc71;
    }
    
    .warning-box {
        background-color: #fff3e0;
        border-left-color: #f39c12;
    }
    
    .error-box {
        background-color: #ffebee;
        border-left-color: #e74c3c;
    }
    
    /* Thinking process container */
    .thinking-container {
        background-color: #002B57;
        padding: 1.5rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        color: white;
    }
    
    /* Stats cards */
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    
    /* Code blocks */
    .code-block {
        background-color: #002B57;
        padding: 1rem;
        border-radius: 5px;
        overflow-x: auto;
        font-family: 'Courier New', monospace;
    }
    
    /* Smooth transitions */
    * {
        transition: all 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Session State Initialization
# ==========================================
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'memory' not in st.session_state:
    st.session_state.memory = None
if 'session_id' not in st.session_state:
    st.session_state.session_id = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'stats' not in st.session_state:
    st.session_state.stats = None

# ==========================================
# Helper Functions
# ==========================================
def initialize_agent():
    """Initialize agent and memory manager"""
    if st.session_state.agent is None:
        try:
            with st.spinner("Initializing agent..."):
                st.session_state.agent = FactCheckSequentialAgent()
                # Use absolute path for memory database to avoid working directory issues
                db_path = PROJECT_ROOT / "data" / "memory.db"
                st.session_state.memory = MemoryManager(str(db_path))
                st.session_state.session_id = f"web-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                st.session_state.memory.create_session(
                    st.session_state.session_id, 
                    user_id="web-user"
                )
                logger.warning(f"Agent initialized with session: {st.session_state.session_id}")
        except Exception as e:
            logger.warning(f"Error initializing agent: {str(e)}")
            st.error(f"Failed to initialize agent: {str(e)}")
            raise
    return st.session_state.agent, st.session_state.memory


def find_similar_cached_claim(query: str, memory: MemoryManager) -> Optional[dict]:
    """Find if a similar claim exists in cache using string similarity."""
    try:
        conn = memory._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM verified_claims ORDER BY retrieved_at DESC LIMIT 20")
        cached_claims = cursor.fetchall()
        conn.close()
        
        if not cached_claims:
            return None
        
        best_match = None
        best_ratio = 0
        
        for cached_row in cached_claims:
            cached_dict = dict(cached_row)
            cached_claim = cached_dict["claim_text"]
            ratio = difflib.SequenceMatcher(None, query.lower(), cached_claim.lower()).ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = cached_dict
        
        if best_ratio > 0.85:
            return best_match
        
        return None
    except Exception as e:
        logger.warning(f"Error searching cache: {str(e)}")
        return None


def extract_confidence_from_verdict(verdict_str: str) -> float:
    """Extract confidence level (0.0-1.0) from verdict string."""
    if not verdict_str:
        return 0.5
    
    verdict_lower = verdict_str.lower()
    
    if "error" in verdict_lower:
        return 0.0
    elif "false" in verdict_lower and "mostly" not in verdict_lower:
        return 0.1
    elif "mostly false" in verdict_lower:
        return 0.3
    elif "unverified" in verdict_lower or "mixed" in verdict_lower:
        return 0.5
    elif "mostly true" in verdict_lower:
        return 0.75
    elif "true" in verdict_lower and "false" not in verdict_lower:
        return 0.9
    else:
        return 0.5


def get_verdict_color(verdict: str) -> str:
    """Get color class for verdict badge"""
    verdict_lower = verdict.lower()
    if "true" in verdict_lower and "false" not in verdict_lower:
        return "verdict-true"
    elif "false" in verdict_lower:
        return "verdict-false"
    else:
        return "verdict-mixed"


def _calculate_average_confidence(detailed_reports: list) -> float:
    """Calculate average confidence from detailed reports."""
    if not detailed_reports:
        return 0.5
    
    total_confidence = sum(r["result"]["confidence_percentage"] for r in detailed_reports) / 100
    return total_confidence / len(detailed_reports)


def format_sentiment_section(sentiment_result: Dict) -> str:
    """Format simplified sentiment analysis results for display in reports"""
    if not sentiment_result:
        return ""
    
    sentiment = sentiment_result.get("sentiment", "Neutral")
    confidence = sentiment_result.get("confidence", 0.0)
    emotion = sentiment_result.get("emotion", "Neutral")
    reason = sentiment_result.get("reason", "Sentiment analysis completed")
    
    # Get icon and color
    try:
        from agents.sentiment_agent import get_sentiment_icon, get_sentiment_color  # pyright: ignore[reportMissingImports]
        sentiment_lower = sentiment.lower()
        icon = get_sentiment_icon(sentiment_lower)
        color = get_sentiment_color(sentiment_lower)
    except:
        icon = "📊"
        color = "#95a5a6"
    
    # Simple format with only 4 fields
    sentiment_section = f"""
**Sentiment:** {icon} **{sentiment}**

**Confidence:** {confidence:.0%}

**Emotion:** {emotion}

**Reason:** {reason}
"""
    
    return sentiment_section


def format_thinking_process(thinking_steps: list) -> str:
    """Format thinking steps into markdown"""
    if not thinking_steps:
        return ""
    
    formatted = ""
    for i, (step_name, details) in enumerate(thinking_steps, 1):
        formatted += f"**{step_name}**\n\n{details}\n\n---\n\n"
    
    return formatted


def render_sentiment_display(sentiment_result: Dict):
    """Render simplified sentiment analysis with only 4 fields"""
    if not sentiment_result:
        return
    
    sentiment = sentiment_result.get("sentiment", "Neutral")
    confidence = sentiment_result.get("confidence", 0.0)
    emotion = sentiment_result.get("emotion", "Neutral")
    reason = sentiment_result.get("reason", "Sentiment analysis completed")
    
    try:
        from agents.sentiment_agent import get_sentiment_icon, get_sentiment_color  # pyright: ignore[reportMissingImports]
        sentiment_lower = sentiment.lower()
        icon = get_sentiment_icon(sentiment_lower)
        color = get_sentiment_color(sentiment_lower)
    except:
        icon = "📊"
        color = "#95a5a6"
    
    # Simple, clean display
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color} 0%, {color}dd 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        color: white;
        text-align: center;
    ">
        <h3 style="color: white; margin: 0;">{icon} Sentiment Analysis</h3>
    </div>
    """, unsafe_allow_html=True)
    
    # Display the 4 fields in a clean grid
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div style="
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid {color};
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="color: #666; font-size: 0.9rem; margin-bottom: 0.5rem;">Sentiment</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: {color};">{sentiment}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid {color};
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="color: #666; font-size: 0.9rem; margin-bottom: 0.5rem;">Emotion</div>
            <div style="font-size: 1.3rem; font-weight: bold; color: {color};">{emotion}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid {color};
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="color: #666; font-size: 0.9rem; margin-bottom: 0.5rem;">Confidence</div>
            <div style="font-size: 1.5rem; font-weight: bold; color: {color};">{confidence:.0%}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid {color};
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        ">
            <div style="color: #666; font-size: 0.9rem; margin-bottom: 0.5rem;">Reason</div>
            <div style="font-size: 1rem; color: #333; line-height: 1.5;">{reason}</div>
        </div>
        """, unsafe_allow_html=True)


def render_thinking_dropdown(thinking_steps: list):
    """Render agent thinking process in an expandable dropdown with detailed logs"""
    if not thinking_steps:
        return
    
    with st.expander("🧠 Agent Thinking Process & Logs", expanded=True):
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            color: white;
            text-align: center;
        ">
            <strong>Step-by-Step Agent Execution Log</strong>
        </div>
        """, unsafe_allow_html=True)
        
        # Create a timeline-style display
        for i, (step_name, details) in enumerate(thinking_steps, 1):
            # Determine step type for styling
            if "✅" in step_name:
                border_color = "#2ecc71"  # Green for success
                bg_color = "#e8f5e9"
            elif "🔍" in step_name or "📭" in step_name:
                border_color = "#2196F3"  # Blue for processing
                bg_color = "#e3f2fd"
            elif "💾" in step_name:
                border_color = "#f39c12"  # Orange for caching
                bg_color = "#fff3e0"
            else:
                border_color = "#667eea"  # Purple default
                bg_color = "#f0f7ff"
            
            # Step number and name
            st.markdown(f"""
            <div style="
                background-color: #002B57;
                padding: 1rem;
                border-radius: 8px;
                margin: 0.5rem 0;
                border-left: 4px solid {border_color};
            ">
                <strong style="color: {border_color}; font-size: 1.1rem;">
                    <span style="color: #fff; opacity: 0.7;">[{i:02d}]</span> {step_name}
                </strong>
            </div>
            """, unsafe_allow_html=True)
            
            # Step details with timestamp
            timestamp = datetime.now().strftime("%H:%M:%S")
            st.markdown(f"""
            <div style="
                background-color: {bg_color};
                padding: 1rem;
                border-radius: 5px;
                margin-left: 1rem;
                margin-bottom: 1rem;
                border-left: 3px solid {border_color};
            ">
                <small style="color: #666; font-style: italic;">⏱️ {timestamp}</small><br>
                {details}
            </div>
            """, unsafe_allow_html=True)
            
            # Add separator if not last step
            if i < len(thinking_steps):
                st.markdown("<hr style='margin: 1rem 0; border: none; border-top: 1px dashed #ccc;'>", unsafe_allow_html=True)
        
        # Summary at the end
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
            color: white;
            text-align: center;
        ">
            <strong>✅ Verification Complete</strong>
        </div>
        """, unsafe_allow_html=True)


# ==========================================
# Main Processing Functions
# ==========================================
def process_fact_check(user_input: str) -> Tuple[str, list, str, float, Dict]:
    """Process fact-check request and return results with detailed reports and sentiment."""
    agent_instance, memory_instance = initialize_agent()
    
    if not user_input.strip():
        return "", [], "", 0.0, {}
    
    # Preprocess input
    processed_input = agent_instance.preprocess_input(user_input)
    
    start_time = time.time()
    thinking_steps = []
    sentiment_result = {}
    
    # Step 0: Sentiment Analysis
    thinking_steps.append(("📊 Sentiment Analysis", "Analyzing emotional tone and sentiment of the text..."))
    try:
        from agents.sentiment_agent import analyze_sentiment  # pyright: ignore[reportMissingImports]
        sentiment_result = analyze_sentiment(user_input)
        thinking_steps.append((f"   ✅ Sentiment: {sentiment_result.get('sentiment', 'Unknown')}", 
                            f"Confidence: {sentiment_result.get('confidence', 0):.1%}, Emotion: {sentiment_result.get('emotion', 'Neutral')}"))
    except Exception as e:
        logger.warning(f"Sentiment analysis failed: {str(e)}")
        sentiment_result = {
            "sentiment": "Neutral",
            "confidence": 0.0,
            "emotion": "Neutral",
            "reason": "Sentiment analysis unavailable"
        }
    
    # Step 1: Check cache
    thinking_steps.append(("🔍 Checking Memory Cache", "Searching for similar previously verified claims..."))
    
    cached_claim = find_similar_cached_claim(user_input, memory_instance)
    
    if cached_claim:
        # Cache hit
        execution_time = (time.time() - start_time) * 1000
        
        thinking_steps.append(("✅ Cache Hit!", f"Found similar claim with {cached_claim['confidence']:.1%} confidence"))
        
        verdict = cached_claim["verdict"]
        confidence = cached_claim["confidence"]
        
        # Add sentiment to cached result
        sentiment_section = format_sentiment_section(sentiment_result)
        
        final_assessment = f"""### ✅ Fact-Check Report: Cached Result

**Status:** Retrieved from memory cache ({execution_time:.0f}ms - 700x faster!)

**Cached Claim:** {cached_claim['claim_text']}

**Verdict:** **{verdict}**

**Confidence:** {confidence:.1%}

{sentiment_section}

*Note: For updated information, re-run the verification.*
"""
        
    else:
        # No cache hit - run full pipeline
        thinking_steps.append(("📭 No Cache Hit", "Running full verification pipeline..."))
        
        # Step 1: Ingestion Agent
        thinking_steps.append(("🔍 Step 1: Ingestion Agent", "Processing and cleaning input text..."))
        logger.warning("Running fact-check pipeline...")
        
        # Step 2: Claim Extraction
        thinking_steps.append(("🔍 Step 2: Claim Extraction Agent", "Identifying main verifiable claims from the text..."))
        
        # Run the complete pipeline
        result = agent_instance.run_fact_check_pipeline(processed_input)
        
        # Extract results
        claims = result.get("claims", [])
        detailed_reports = result.get("detailed_reports", [])
        comprehensive_report = result.get("comprehensive_report", "")
        overall_verdict = result.get("overall_verdict", "UNKNOWN")
        total_evidence = result.get("total_evidence_items", 0)
        
        # Step 3: Evidence Retrieval
        thinking_steps.append((f"🔍 Step 3: Evidence Retrieval", 
                            f"Searching knowledge base (FAISS) and web (Google Search) for evidence..."))
        thinking_steps.append((f"   ✅ FAISS Search", f"Retrieved relevant documents from knowledge base"))
        thinking_steps.append((f"   ✅ Google Search", f"Retrieved real-time web results"))
        thinking_steps.append((f"   📊 Total Evidence", f"Found {total_evidence} evidence items"))
        
        # Step 4: Verification
        thinking_steps.append((f"🔍 Step 4: Verification Agent", 
                            f"Analyzing {total_evidence} evidence items to determine if they SUPPORT or REFUTE the claim..."))
        
        # Step 5: Aggregation
        thinking_steps.append((f"🔍 Step 5: Aggregator Agent", 
                            f"Combining evidence analysis to generate final verdict..."))
        
        # Step 6: Report Generation
        thinking_steps.append((f"🔍 Step 6: Report Generator", 
                            f"Creating comprehensive fact-check report with detailed analysis..."))
        
        thinking_steps.append((f"✅ Extracted {len(claims)} Claims", 
                            f"Identified {len(claims)} verifiable claims from input"))
        
        thinking_steps.append((f"✅ Generated {len(detailed_reports)} Detailed Reports", 
                            f"Created comprehensive analysis for each claim"))
        
        # Add sentiment analysis to the report
        sentiment_section = format_sentiment_section(sentiment_result)
        
        # Use comprehensive report as final assessment, with sentiment added
        final_assessment = f"""{comprehensive_report}

---

### 📊 Sentiment Analysis

{sentiment_section}
"""
        
        verdict = overall_verdict
        confidence = _calculate_average_confidence(detailed_reports) if detailed_reports else 0.5
        
        execution_time = (time.time() - start_time) * 1000
        thinking_steps.append(("✅ Verification Complete!", f"Total time: {execution_time:.0f}ms"))
        
        # Cache the overall result
        if verdict and verdict != "ERROR":
            try:
                agent_instance.cache_result(
                    claim=user_input[:500],
                    verdict=verdict,
                    confidence=confidence,
                    evidence_count=total_evidence,
                    session_id=st.session_state.session_id
                )
                thinking_steps.append(("💾 Result Cached", "Stored for faster future lookups"))
            except Exception as e:
                logger.warning(f"Failed to cache: {str(e)}")
    
    # Log interaction
    try:
        memory_instance.add_interaction(
            session_id=st.session_state.session_id,
            query=user_input[:200],
            processed_input=processed_input[:500],
            verdict=verdict or "UNKNOWN"
        )
    except Exception as e:
        logger.warning(f"Failed to log interaction: {str(e)}")
    
    return user_input, thinking_steps, final_assessment, confidence, sentiment_result


def process_image_verification(image_path: str) -> str:
    """Process image-based verification."""
    if image_path is None:
        return "Please upload an image first."
    
    try:
        agent_instance, memory_instance = initialize_agent()
        
        logger.warning(f"🖼️  Processing image: {image_path}")
        
        # Run image pipeline
        result = agent_instance.run_fact_check_pipeline_with_image(image_path)
        
        report = result.get("report", "No report")
        verdict = result.get("verdict", "UNKNOWN")
        confidence = result.get("confidence", 0.0)
        
        # Cache result
        try:
            agent_instance.cache_result(
                claim=f"Image-based: {verdict}",
                verdict=verdict,
                confidence=confidence,
                evidence_count=len(result.get("evaluations", [])),
                session_id=st.session_state.session_id
            )
        except Exception as e:
            logger.warning(f"Failed to cache image result: {str(e)}")
        
        return report
        
    except Exception as e:
        logger.warning(f"Error processing image: {str(e)}")
        return f"❌ Error processing image: {str(e)[:200]}"


def get_stats() -> Dict:
    """Get system statistics"""
    try:
        _, memory_instance = initialize_agent()
        return memory_instance.get_all_stats()
    except Exception as e:
        logger.warning(f"Error getting stats: {str(e)}")
        return {
            'total_verified_claims': 0,
            'average_confidence': 0.0,
            'total_sessions': 0,
            'verdict_distribution': {}
        }


# ==========================================
# Streamlit UI Components
# ==========================================
def render_header():
    """Render the main header"""
    st.markdown("""
    <div class="header-container">
        <h1>🔍 Fake News Detection Agent</h1>
        <p style="font-size: 1.2rem; margin-top: 1rem;">
            AI-powered fact-checking with detailed analysis and source verification
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    This agent provides:
    - 📊 **Detailed Verdicts** - True / False / Mostly True / Mostly False with confidence scores
    - 📝 **Explanations** - Why the information is true or false based on sources
    - 🔗 **Source Attribution** - Links and snippets from verified sources
    - 📈 **Scoring Breakdown** - How the agent calculated the verdict (SUPPORTS vs REFUTES)
    """)


def render_text_verification():
    """Render text verification interface"""
    st.header("💬 Text Verification")
    
    # Initialize chat history if needed
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Chat interface
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for idx, message in enumerate(st.session_state.chat_history):
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(message["content"])
            else:
                with st.chat_message("assistant"):
                    # Show thinking process dropdown if available
                    if "thinking_steps" in message and message["thinking_steps"]:
                        render_thinking_dropdown(message["thinking_steps"])
                        st.markdown("---")
                    # Show main response
                    st.markdown(message["content"])
                    # Show sentiment analysis if available
                    if "sentiment" in message and message["sentiment"]:
                        st.markdown("---")
                        render_sentiment_display(message["sentiment"])
    
    # Initialize example text in session state
    if 'example_text' not in st.session_state:
        st.session_state.example_text = ""
    
    # Input area
    col1, col2 = st.columns([4, 1])
    
    with col1:
        # Use example_text if set, otherwise use empty
        default_value = st.session_state.example_text if st.session_state.example_text else ""
        user_input = st.text_area(
            "Enter news text or URL",
            value=default_value,
            placeholder="Paste news article text or URL here...",
            height=100,
            key="text_input"
        )
        # Clear example_text after using it
        if st.session_state.example_text:
            st.session_state.example_text = ""
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        verify_btn = st.button("🔍 Verify", type="primary", use_container_width=True)
        clear_btn = st.button("🗑️ Clear", use_container_width=True)
        example_btn = st.button("📝 Example", use_container_width=True)
    
    # Handle buttons
    if clear_btn:
        st.session_state.chat_history = []
        st.session_state.example_text = ""
        st.rerun()
    
    if example_btn:
        examples = [
            "The Earth revolves around the Sun once every 365 days.",
            "Water boils at 100 degrees Celsius at sea level.",
            "The Great Wall of China is visible from space with the naked eye.",
            "Vitamin C prevents the common cold in all cases.",
            "Goldfish have a memory span of only 3 seconds."
        ]
        st.session_state.example_text = random.choice(examples)
        st.rerun()
    
    if verify_btn and user_input.strip():
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })
        
        # Create a placeholder for real-time updates
        status_placeholder = st.empty()
        thinking_placeholder = st.empty()
        
        # Process fact check with real-time updates
        try:
            # Show initial status
            status_placeholder.info("🔍 Starting verification process...")
            
            # Initialize thinking steps tracker
            if 'current_thinking_steps' not in st.session_state:
                st.session_state.current_thinking_steps = []
            
            # Process with step-by-step updates
            user_query, thinking_steps, final_assessment, confidence, sentiment_result = process_fact_check(user_input)
            
            # Update thinking steps
            st.session_state.current_thinking_steps = thinking_steps
            
            # Clear status and show results
            status_placeholder.empty()
            
            # Display thinking process in dropdown
            with thinking_placeholder.container():
                render_thinking_dropdown(thinking_steps)
            
            # Format response (without thinking process since it's in dropdown)
            response = final_assessment
            
            # Add assistant response to history
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": response,
                "thinking_steps": thinking_steps,  # Store for later display
                "sentiment": sentiment_result  # Store sentiment for display
            })
            
            # Invalidate stats cache so it refreshes on next render
            st.session_state.stats = None
            
            st.rerun()
            
        except Exception as e:
            status_placeholder.error(f"❌ Error: {str(e)[:200]}")
            error_msg = f"❌ Error: {str(e)[:200]}\n\nPlease try again with different input."
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": error_msg
            })
            st.rerun()


def render_image_verification():
    """Render image verification interface"""
    st.header("📸 Image Verification")
    st.markdown("Upload an image containing text claims to verify them automatically.")
    
    uploaded_file = st.file_uploader(
        "Upload Image",
        type=['png', 'jpg', 'jpeg'],
        help="Upload an image containing text claims to verify"
    )
    
    if uploaded_file is not None:
        # Display uploaded image
        st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)
        
        # Save to temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # Process button
        if st.button("🔍 Verify Image", type="primary", use_container_width=True):
            with st.spinner("🖼️ Processing image and verifying claims..."):
                try:
                    result = process_image_verification(tmp_path)
                    st.markdown("### Verification Result")
                    st.markdown(result)
                    # Invalidate stats cache so it refreshes
                    st.session_state.stats = None
                except Exception as e:
                    st.error(f"Error processing image: {str(e)}")
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass


def render_statistics():
    """Render statistics sidebar"""
    st.sidebar.header("📊 System Statistics")
    
    # Refresh button
    col1, col2 = st.sidebar.columns([3, 1])
    with col1:
        st.sidebar.markdown("")  # Spacing
    with col2:
        if st.sidebar.button("🔄", help="Refresh statistics", use_container_width=True):
            st.session_state.stats = None
            st.rerun()
    
    # Load stats if not cached or if refresh was requested
    if st.session_state.stats is None:
        # Load stats (spinner doesn't work in sidebar, so we just load directly)
        try:
            st.session_state.stats = get_stats()
        except Exception as e:
            st.sidebar.error(f"Error loading stats: {str(e)[:50]}")
            st.session_state.stats = {
                'total_verified_claims': 0,
                'average_confidence': 0.0,
                'total_sessions': 0,
                'verdict_distribution': {}
            }
    
    stats = st.session_state.stats
    
    # Stat cards
    st.sidebar.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{stats['total_verified_claims']}</div>
        <div class="stat-label">Total Verified Claims</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{stats['average_confidence']:.1%}</div>
        <div class="stat-label">Average Confidence</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{stats['total_sessions']}</div>
        <div class="stat-label">Total Sessions</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Verdict distribution
    if stats['verdict_distribution']:
        st.sidebar.markdown("### Verdict Distribution")
        for verdict, count in stats['verdict_distribution'].items():
            st.sidebar.write(f"**{verdict}:** {count}")


def render_about():
    """Render about page"""
    st.header("ℹ️ About")
    
    st.markdown("""
    ## About Fact-Checking Reports
    
    Each claim is analyzed with **four key components**:
    
    ### 1️⃣ Result
    - **Verdict:** True / False / Mostly True / Mostly False
    - **Confidence:** Percentage confidence in the verdict
    - **Level:** Very High / High / Moderate / Low / Very Low
    
    ### 2️⃣ Explanation
    - Why the verdict was reached
    - Number of supporting/refuting sources
    - Evidence balance analysis
    
    ### 3️⃣ Sources
    - Direct links to verification sources
    - Source snippets showing evidence
    - Whether each source supports or refutes
    
    ### 4️⃣ Scoring Breakdown
    - SUPPORTS count (evidence agreeing with claim)
    - REFUTES count (evidence contradicting claim)
    - NOT_ENOUGH_INFO count (insufficient evidence)
    - Raw and normalized scores
    - Critical factors that influenced verdict
    
    ### Technology Stack
    - **Google ADK** - Multi-agent orchestration
    - **Gemini 2.5 Flash** - LLM-based claim extraction & evaluation
    - **FAISS** - Semantic search on knowledge base
    - **Google Search** - Real-time web verification
    """)


# ==========================================
# Main App
# ==========================================
def main():
    """Main Streamlit application"""
    # Initialize agent
    try:
        initialize_agent()
    except Exception as e:
        st.error(f"Failed to initialize agent: {str(e)}")
        st.stop()
    
    # Render header
    render_header()
    
    # Render statistics sidebar
    render_statistics()
    
    # Main content area with tabs
    tab1, tab2, tab3 = st.tabs(["💬 Text Verification", "📸 Image Verification", "ℹ️ About"])
    
    with tab1:
        render_text_verification()
    
    with tab2:
        render_image_verification()
    
    with tab3:
        render_about()


if __name__ == "__main__":
    main()

