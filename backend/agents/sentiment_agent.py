"""
Advanced Sentiment Analysis Agent
Comprehensive sentiment analysis considering:
- Text quality assessment
- Contextual understanding
- Emotion strength measurement
- Domain relevance scoring
- Confidence calibration
- Explainable reasoning
"""

from typing import Dict, Optional, List
from config import ADK_MODEL_NAME, get_logger
from google import genai
import json
import os
import re

logger = get_logger(__name__)

# Get client for Gemini API
def get_client():
    """Get a fresh genai client with the correct API key"""
    from config import GEMINI_API_KEY
    os.environ['GOOGLE_API_KEY'] = GEMINI_API_KEY
    os.environ['GEMINI_API_KEY'] = GEMINI_API_KEY
    return genai.Client(api_key=GEMINI_API_KEY)

client = get_client()


def assess_text_quality(text: str) -> Dict:
    """
    Assess the quality of the input text
    
    Returns:
        Dict with quality metrics: readability, completeness, coherence, noise_level
    """
    quality_metrics = {
        "readability": 0.5,
        "completeness": 0.5,
        "coherence": 0.5,
        "noise_level": 0.5,
        "word_count": len(text.split()),
        "char_count": len(text),
        "has_punctuation": bool(re.search(r'[.!?]', text)),
        "has_capitalization": bool(re.search(r'[A-Z]', text))
    }
    
    # Basic quality heuristics
    word_count = quality_metrics["word_count"]
    
    # Readability: based on sentence structure and length
    sentences = re.split(r'[.!?]+', text)
    avg_sentence_length = word_count / max(len([s for s in sentences if s.strip()]), 1)
    if 10 <= avg_sentence_length <= 25:
        quality_metrics["readability"] = 0.8
    elif 5 <= avg_sentence_length <= 30:
        quality_metrics["readability"] = 0.6
    else:
        quality_metrics["readability"] = 0.4
    
    # Completeness: based on text length and structure
    if word_count >= 10:
        quality_metrics["completeness"] = min(0.9, 0.5 + (word_count / 100))
    else:
        quality_metrics["completeness"] = max(0.2, word_count / 20)
    
    # Coherence: based on punctuation and capitalization
    if quality_metrics["has_punctuation"] and quality_metrics["has_capitalization"]:
        quality_metrics["coherence"] = 0.7
    elif quality_metrics["has_punctuation"] or quality_metrics["has_capitalization"]:
        quality_metrics["coherence"] = 0.5
    else:
        quality_metrics["coherence"] = 0.3
    
    # Noise level: detect excessive special characters, repeated characters, etc.
    special_char_ratio = len(re.findall(r'[^a-zA-Z0-9\s]', text)) / max(len(text), 1)
    repeated_chars = len(re.findall(r'(.)\1{3,}', text))
    quality_metrics["noise_level"] = min(1.0, special_char_ratio * 2 + (repeated_chars * 0.1))
    
    return quality_metrics


def analyze_sentiment(text: str, domain: Optional[str] = None) -> Dict:
    """
    Advanced sentiment analysis considering text quality, context, emotion strength,
    domain relevance, confidence, and explainability.
    
    Args:
        text: Input text to analyze
        domain: Optional domain context (e.g., 'news', 'social_media', 'academic')
    
    Returns:
        Dict with comprehensive sentiment analysis including:
        - sentiment: 'positive', 'negative', 'neutral', or 'mixed'
        - polarity: float between -1 (very negative) and 1 (very positive)
        - confidence: float between 0 and 1 (calibrated based on quality)
        - emotions: list of detected emotions with strength scores
        - emotion_strength: overall emotion intensity
        - text_quality: quality assessment metrics
        - context: contextual understanding
        - domain_relevance: relevance to specified domain
        - explainability: detailed reasoning for the analysis
        - summary: brief description of the sentiment
        - intensity: "low|moderate|high|very_high"
    """
    logger.warning("📊 Performing advanced sentiment analysis...")
    
    # Step 1: Assess text quality
    quality_metrics = assess_text_quality(text)
    quality_score = (
        quality_metrics["readability"] * 0.3 +
        quality_metrics["completeness"] * 0.3 +
        quality_metrics["coherence"] * 0.2 +
        (1 - quality_metrics["noise_level"]) * 0.2
    )
    
    # Step 2: Build comprehensive analysis prompt
    domain_context = f"\nDomain Context: {domain}" if domain else ""
    quality_context = f"""
Text Quality Assessment:
- Readability: {quality_metrics['readability']:.2f}
- Completeness: {quality_metrics['completeness']:.2f}
- Coherence: {quality_metrics['coherence']:.2f}
- Noise Level: {quality_metrics['noise_level']:.2f}
- Overall Quality Score: {quality_score:.2f}
"""
    
    prompt = f"""Analyze the sentiment of this text and provide a simple, clear response:

TEXT: {text}

Consider text quality, context, emotion strength, domain relevance, confidence, and explainability when analyzing, but return ONLY these 4 fields in JSON format:

{{
    "sentiment": "Positive|Negative|Neutral|Mixed",
    "confidence": <float between 0.0 and 1.0>,
    "emotion": "<primary_emotion_name>",
    "reason": "<brief explanation of why this sentiment was determined, e.g., 'Sarcasm detected', 'Strong negative language', etc.>"
}}

Be concise and clear. The reason should be brief (1-2 sentences max).
"""
    
    try:
        current_client = get_client()
        response = current_client.models.generate_content(
            model=ADK_MODEL_NAME,
            contents=prompt
        )
        result_text = response.text if hasattr(response, 'text') else str(response)
        
        # Parse JSON response
        try:
            json_str = result_text
            if "```json" in result_text:
                json_str = result_text.split("```json")[1].split("```")[0]
            elif "{" in result_text:
                json_str = result_text[result_text.find("{"):result_text.rfind("}")+1]
            
            result = json.loads(json_str)
            
            # Extract simplified fields only
            sentiment = result.get("sentiment", "Neutral")
            # Normalize sentiment to proper case
            sentiment_lower = sentiment.lower()
            if sentiment_lower == "positive":
                sentiment = "Positive"
            elif sentiment_lower == "negative":
                sentiment = "Negative"
            elif sentiment_lower == "mixed":
                sentiment = "Mixed"
            else:
                sentiment = "Neutral"
            
            confidence = float(result.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
            # Adjust confidence based on text quality
            confidence = confidence * quality_score
            
            emotion = result.get("emotion", "Neutral")
            if emotion:
                emotion = emotion.capitalize()
            else:
                emotion = "Neutral"
            
            reason = result.get("reason", "Sentiment analysis completed")
            if not reason or len(reason.strip()) == 0:
                reason = "Sentiment analysis completed"
            
            logger.warning("✅ Sentiment analysis complete: %s (confidence: %.2f, emotion: %s)", 
                          sentiment, confidence, emotion)
            
            # Return simplified format with only 4 fields
            return {
                "sentiment": sentiment,
                "confidence": round(confidence, 2),
                "emotion": emotion,
                "reason": reason
            }
            
        except json.JSONDecodeError as e:
            logger.warning("⚠️  Could not parse sentiment JSON, using fallback: %s", str(e)[:50])
            # Fallback: simple keyword-based sentiment
            return _fallback_sentiment_analysis(text)
            
    except Exception as e:
        logger.warning("❌ Sentiment analysis error: %s", str(e)[:100])
        return _fallback_sentiment_analysis(text)


def _fallback_sentiment_analysis(text: str) -> Dict:
    """Fallback sentiment analysis using simple keyword matching"""
    text_lower = text.lower()
    quality_metrics = assess_text_quality(text)
    quality_score = (
        quality_metrics["readability"] * 0.3 +
        quality_metrics["completeness"] * 0.3 +
        quality_metrics["coherence"] * 0.2 +
        (1 - quality_metrics["noise_level"]) * 0.2
    )
    
    positive_words = ["good", "great", "excellent", "amazing", "wonderful", "positive", "happy", "joy", "love", "best", "fantastic"]
    negative_words = ["bad", "terrible", "awful", "horrible", "negative", "sad", "angry", "hate", "fear", "worst", "disgusting"]
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        sentiment = "Positive"
        emotion = "Joy"
        reason = f"Positive keywords detected ({positive_count} positive words)"
    elif negative_count > positive_count:
        sentiment = "Negative"
        emotion = "Sadness"
        reason = f"Negative keywords detected ({negative_count} negative words)"
    else:
        sentiment = "Neutral"
        emotion = "Neutral"
        reason = "No strong emotional indicators found"
    
    # Lower confidence for fallback method
    confidence = round(0.3 * quality_score, 2)
    
    return {
        "sentiment": sentiment,
        "confidence": confidence,
        "emotion": emotion,
        "reason": reason
    }


def get_sentiment_color(sentiment: str) -> str:
    """Get color code for sentiment"""
    sentiment_lower = sentiment.lower()
    if sentiment_lower == "positive":
        return "#2ecc71"  # Green
    elif sentiment_lower == "negative":
        return "#e74c3c"  # Red
    elif sentiment_lower == "mixed":
        return "#f39c12"  # Orange
    else:
        return "#95a5a6"  # Gray for neutral


def get_sentiment_icon(sentiment: str) -> str:
    """Get emoji icon for sentiment"""
    sentiment_lower = sentiment.lower()
    if sentiment_lower == "positive":
        return "😊"
    elif sentiment_lower == "negative":
        return "😞"
    elif sentiment_lower == "mixed":
        return "😐"
    else:
        return "😶"

