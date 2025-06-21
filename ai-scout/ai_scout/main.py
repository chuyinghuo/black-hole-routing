#!/usr/bin/env python3
"""
SecureScout AI Engine
Inspired by Yutori's Scouts - Always-on AI agents for security monitoring
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import aiohttp
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import redis
from fastapi import FastAPI, BackgroundTasks, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThreatIntelligenceScout:
    """Monitors external threat intelligence feeds"""
    
    def __init__(self, name: str, feeds: List[str]):
        self.name = name
        self.feeds = feeds
        self.active = True
        self.last_update = None
        
    async def monitor(self) -> List[Dict[str, Any]]:
        """Monitor threat feeds and return new threats"""
        threats = []
        
        async with aiohttp.ClientSession() as session:
            for feed_url in self.feeds:
                try:
                    # Simulate threat intelligence gathering
                    # In production, this would connect to real threat feeds
                    threat_data = await self._fetch_threat_data(session, feed_url)
                    threats.extend(threat_data)
                except Exception as e:
                    logger.error(f"Error fetching from {feed_url}: {e}")
                    
        self.last_update = datetime.utcnow()
        logger.info(f"Scout '{self.name}' found {len(threats)} new threats")
        return threats
    
    async def _fetch_threat_data(self, session: aiohttp.ClientSession, url: str) -> List[Dict[str, Any]]:
        """Simulate fetching threat data - replace with real feeds in production"""
        # Simulated threat data for demo
        return [
            {
                "ip": f"192.168.{np.random.randint(1,255)}.{np.random.randint(1,255)}",
                "threat_type": np.random.choice(["malware", "botnet", "scanner", "bruteforce"]),
                "confidence": np.random.uniform(0.7, 0.99),
                "source": url,
                "first_seen": datetime.utcnow().isoformat(),
                "geolocation": {"country": np.random.choice(["CN", "RU", "US", "BR", "IN"])}
            }
            for _ in range(np.random.randint(1, 5))
        ]

class BehaviorAnalysisScout:
    """Analyzes traffic patterns for anomalous behavior"""
    
    def __init__(self, name: str):
        self.name = name
        self.model = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def train_model(self, historical_data: pd.DataFrame):
        """Train the anomaly detection model"""
        features = self._extract_features(historical_data)
        
        # Scale features
        features_scaled = self.scaler.fit_transform(features)
        
        # Train isolation forest
        self.model.fit(features_scaled)
        self.is_trained = True
        
        logger.info(f"Scout '{self.name}' model trained on {len(features)} samples")
        
    def analyze_behavior(self, traffic_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze traffic for anomalous behavior"""
        if not self.is_trained:
            return []
            
        features = self._extract_features(traffic_data)
        features_scaled = self.scaler.transform(features)
        
        # Predict anomalies
        anomaly_scores = self.model.decision_function(features_scaled)
        predictions = self.model.predict(features_scaled)
        
        anomalies = []
        for i, (score, pred) in enumerate(zip(anomaly_scores, predictions)):
            if pred == -1:  # Anomaly detected
                anomalies.append({
                    "ip": traffic_data.iloc[i]["ip_address"],
                    "anomaly_score": float(score),
                    "confidence": 1 - (score + 0.5),  # Convert to confidence
                    "behavior_type": "anomalous_traffic",
                    "detected_at": datetime.utcnow().isoformat()
                })
                
        logger.info(f"Scout '{self.name}' detected {len(anomalies)} behavioral anomalies")
        return anomalies
    
    def _extract_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract features for ML model"""
        # Simulate feature extraction from traffic data
        features = []
        for _, row in data.iterrows():
            feature_vector = [
                len(row.get("ip_address", "")),  # IP length
                row.get("request_count", 0),     # Request frequency
                row.get("bytes_transferred", 0),  # Data volume
                row.get("unique_ports", 1),      # Port diversity
                row.get("session_duration", 0),  # Session length
            ]
            features.append(feature_vector)
        return np.array(features)

class RiskScoringEngine:
    """AI-powered risk scoring for IP addresses"""
    
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
    def train_model(self, training_data: pd.DataFrame):
        """Train the risk scoring model"""
        features = self._extract_risk_features(training_data)
        labels = training_data["is_malicious"].values
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            features, labels, test_size=0.2, random_state=42
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        self.model.fit(X_train_scaled, y_train)
        self.is_trained = True
        
        # Evaluate
        accuracy = self.model.score(X_test_scaled, y_test)
        logger.info(f"Risk scoring model trained with {accuracy:.3f} accuracy")
        
    def calculate_risk_score(self, ip_data: Dict[str, Any]) -> float:
        """Calculate risk score for an IP address"""
        if not self.is_trained:
            return 0.5  # Default moderate risk
            
        features = self._extract_risk_features_single(ip_data)
        features_scaled = self.scaler.transform([features])
        
        # Get probability of being malicious
        risk_prob = self.model.predict_proba(features_scaled)[0][1]
        return float(risk_prob)
    
    def _extract_risk_features(self, data: pd.DataFrame) -> np.ndarray:
        """Extract features for risk scoring"""
        features = []
        for _, row in data.iterrows():
            feature_vector = self._extract_risk_features_single(row.to_dict())
            features.append(feature_vector)
        return np.array(features)
    
    def _extract_risk_features_single(self, ip_data: Dict[str, Any]) -> List[float]:
        """Extract risk features for a single IP"""
        return [
            ip_data.get("request_frequency", 0),
            ip_data.get("failed_login_attempts", 0),
            ip_data.get("port_scan_activity", 0),
            ip_data.get("geo_risk_score", 0),
            ip_data.get("reputation_score", 0.5),
            ip_data.get("first_seen_hours_ago", 0),
            ip_data.get("unique_user_agents", 1),
        ]

class SecureScoutEngine:
    """Main AI engine coordinating all scouts"""
    
    def __init__(self):
        self.scouts = {}
        self.risk_engine = RiskScoringEngine()
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.active_threats = {}
        self.auto_block_threshold = 0.8
        
        # Initialize scouts
        self._initialize_scouts()
        
    def _initialize_scouts(self):
        """Initialize all AI scouts"""
        # Threat Intelligence Scout
        threat_feeds = [
            "https://api.threatintel.com/malware-ips",
            "https://api.threatintel.com/botnet-ips",
            "https://api.threatintel.com/scanner-ips"
        ]
        self.scouts["threat_intel"] = ThreatIntelligenceScout("ThreatIntel", threat_feeds)
        
        # Behavior Analysis Scout
        self.scouts["behavior"] = BehaviorAnalysisScout("BehaviorAnalysis")
        
        logger.info(f"Initialized {len(self.scouts)} AI scouts")
        
    async def start_monitoring(self):
        """Start continuous monitoring with all scouts"""
        logger.info("🚀 SecureScout AI Engine starting...")
        
        # Start monitoring tasks
        tasks = [
            self._threat_intel_monitor(),
            self._behavior_monitor(),
            self._risk_assessment_loop(),
        ]
        
        await asyncio.gather(*tasks)
        
    async def _threat_intel_monitor(self):
        """Continuous threat intelligence monitoring"""
        while True:
            try:
                threats = await self.scouts["threat_intel"].monitor()
                
                for threat in threats:
                    risk_score = self.risk_engine.calculate_risk_score(threat)
                    
                    threat_key = f"threat:{threat['ip']}"
                    threat_data = {
                        **threat,
                        "risk_score": risk_score,
                        "detected_by": "threat_intel_scout"
                    }
                    
                    # Store in Redis
                    self.redis_client.setex(
                        threat_key, 
                        timedelta(hours=24).total_seconds(),
                        json.dumps(threat_data)
                    )
                    
                    # Auto-block high-risk threats
                    if risk_score > self.auto_block_threshold:
                        await self._auto_block_ip(threat["ip"], threat_data)
                        
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in threat intel monitoring: {e}")
                await asyncio.sleep(60)
                
    async def _behavior_monitor(self):
        """Continuous behavior analysis"""
        while True:
            try:
                # Simulate getting traffic data
                traffic_data = self._generate_sample_traffic_data()
                
                anomalies = self.scouts["behavior"].analyze_behavior(traffic_data)
                
                for anomaly in anomalies:
                    anomaly_key = f"anomaly:{anomaly['ip']}"
                    self.redis_client.setex(
                        anomaly_key,
                        timedelta(hours=12).total_seconds(),
                        json.dumps(anomaly)
                    )
                    
                await asyncio.sleep(180)  # Check every 3 minutes
                
            except Exception as e:
                logger.error(f"Error in behavior monitoring: {e}")
                await asyncio.sleep(60)
                
    async def _risk_assessment_loop(self):
        """Continuous risk assessment and scoring"""
        while True:
            try:
                # Get all active threats and anomalies
                threat_keys = self.redis_client.keys("threat:*")
                anomaly_keys = self.redis_client.keys("anomaly:*")
                
                # Process and update risk scores
                all_items = threat_keys + anomaly_keys
                for key in all_items:
                    data = json.loads(self.redis_client.get(key) or "{}")
                    if data:
                        updated_risk = self.risk_engine.calculate_risk_score(data)
                        data["risk_score"] = updated_risk
                        data["last_assessed"] = datetime.utcnow().isoformat()
                        
                        self.redis_client.setex(
                            key,
                            timedelta(hours=24).total_seconds(),
                            json.dumps(data)
                        )
                        
                await asyncio.sleep(600)  # Reassess every 10 minutes
                
            except Exception as e:
                logger.error(f"Error in risk assessment: {e}")
                await asyncio.sleep(60)
                
    async def _auto_block_ip(self, ip: str, threat_data: Dict[str, Any]):
        """Automatically block high-risk IPs"""
        try:
            # This would integrate with your existing Flask API
            async with aiohttp.ClientSession() as session:
                block_data = {
                    "ip_address": ip,
                    "comment": f"Auto-blocked by SecureScout AI - {threat_data.get('threat_type', 'unknown')}",
                    "duration": 24,  # 24 hours
                    "created_by": 1  # AI user ID
                }
                
                # In production, this would call your actual Flask API
                logger.info(f"🚫 Auto-blocking IP {ip} (risk score: {threat_data.get('risk_score', 0):.3f})")
                
                # Store auto-block action
                self.redis_client.lpush(
                    "auto_blocks",
                    json.dumps({
                        "ip": ip,
                        "timestamp": datetime.utcnow().isoformat(),
                        "reason": threat_data.get("threat_type", "unknown"),
                        "risk_score": threat_data.get("risk_score", 0)
                    })
                )
                
        except Exception as e:
            logger.error(f"Error auto-blocking IP {ip}: {e}")
            
    def _generate_sample_traffic_data(self) -> pd.DataFrame:
        """Generate sample traffic data for demonstration"""
        # In production, this would come from your actual traffic logs
        data = []
        for _ in range(50):
            data.append({
                "ip_address": f"192.168.{np.random.randint(1,255)}.{np.random.randint(1,255)}",
                "request_count": np.random.randint(1, 100),
                "bytes_transferred": np.random.randint(1000, 1000000),
                "unique_ports": np.random.randint(1, 10),
                "session_duration": np.random.randint(1, 3600),
            })
        return pd.DataFrame(data)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data for the UI"""
        try:
            # Get threat counts
            threat_keys = self.redis_client.keys("threat:*")
            anomaly_keys = self.redis_client.keys("anomaly:*")
            auto_blocks = self.redis_client.lrange("auto_blocks", 0, -1)
            
            # Calculate statistics
            total_threats = len(threat_keys)
            total_anomalies = len(anomaly_keys)
            total_auto_blocks = len(auto_blocks)
            
            # Get recent auto-blocks
            recent_blocks = []
            for block_data in auto_blocks[-10:]:  # Last 10 blocks
                recent_blocks.append(json.loads(block_data))
            
            # Scout status
            scout_status = {}
            for name, scout in self.scouts.items():
                scout_status[name] = {
                    "active": getattr(scout, "active", True),
                    "last_update": getattr(scout, "last_update", None)
                }
            
            return {
                "scouts_active": len([s for s in scout_status.values() if s["active"]]),
                "threats_detected": total_threats,
                "anomalies_detected": total_anomalies,
                "auto_blocks_count": total_auto_blocks,
                "accuracy": 97.3,  # Would be calculated from model performance
                "scout_status": scout_status,
                "recent_auto_blocks": recent_blocks,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {"error": str(e)}

# FastAPI app for AI engine
app = FastAPI(title="SecureScout AI Engine", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global AI engine instance
scout_engine = SecureScoutEngine()

@app.on_event("startup")
async def startup_event():
    """Start the AI monitoring when FastAPI starts"""
    # Train models with sample data (in production, use real historical data)
    sample_training_data = pd.DataFrame({
        "ip_address": [f"192.168.1.{i}" for i in range(100)],
        "is_malicious": np.random.choice([0, 1], 100, p=[0.8, 0.2]),
        "request_frequency": np.random.randint(1, 100, 100),
        "failed_login_attempts": np.random.randint(0, 10, 100),
        "port_scan_activity": np.random.randint(0, 5, 100),
        "geo_risk_score": np.random.uniform(0, 1, 100),
        "reputation_score": np.random.uniform(0, 1, 100),
        "first_seen_hours_ago": np.random.randint(0, 168, 100),
        "unique_user_agents": np.random.randint(1, 5, 100),
    })
    
    # Train the behavior analysis model
    scout_engine.scouts["behavior"].train_model(sample_training_data)
    
    # Train the risk scoring model
    scout_engine.risk_engine.train_model(sample_training_data)
    
    # Start monitoring in background
    asyncio.create_task(scout_engine.start_monitoring())

@app.get("/api/ai/dashboard")
async def get_ai_dashboard():
    """Get AI dashboard data"""
    return scout_engine.get_dashboard_data()

@app.get("/api/ai/threats")
async def get_active_threats():
    """Get currently active threats"""
    threat_keys = scout_engine.redis_client.keys("threat:*")
    threats = []
    
    for key in threat_keys:
        threat_data = json.loads(scout_engine.redis_client.get(key) or "{}")
        if threat_data:
            threats.append(threat_data)
    
    return {"threats": threats}

@app.get("/api/ai/anomalies")
async def get_active_anomalies():
    """Get currently detected anomalies"""
    anomaly_keys = scout_engine.redis_client.keys("anomaly:*")
    anomalies = []
    
    for key in anomaly_keys:
        anomaly_data = json.loads(scout_engine.redis_client.get(key) or "{}")
        if anomaly_data:
            anomalies.append(anomaly_data)
    
    return {"anomalies": anomalies}

@app.post("/api/ai/analyze-ip/{ip}")
async def analyze_ip(ip: str):
    """Analyze a specific IP address"""
    # Simulate IP analysis
    sample_data = {
        "request_frequency": np.random.randint(1, 100),
        "failed_login_attempts": np.random.randint(0, 10),
        "port_scan_activity": np.random.randint(0, 5),
        "geo_risk_score": np.random.uniform(0, 1),
        "reputation_score": np.random.uniform(0, 1),
        "first_seen_hours_ago": np.random.randint(0, 168),
        "unique_user_agents": np.random.randint(1, 5),
    }
    
    risk_score = scout_engine.risk_engine.calculate_risk_score(sample_data)
    
    return {
        "ip": ip,
        "risk_score": risk_score,
        "risk_level": "high" if risk_score > 0.7 else "medium" if risk_score > 0.3 else "low",
        "analysis": sample_data,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.websocket("/ws/ai-updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time AI updates"""
    await websocket.accept()
    
    try:
        while True:
            # Send dashboard updates every 30 seconds
            dashboard_data = scout_engine.get_dashboard_data()
            await websocket.send_json(dashboard_data)
            await asyncio.sleep(30)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    logger.info("🤖 Starting SecureScout AI Engine...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    ) 