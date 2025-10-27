"""
Comprehensive Logging System for Strategy AI Backend
Structured logging for all pipeline stages, API calls, costs, and performance
"""
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps


# Configure structured logger
logger = logging.getLogger(__name__)


class AnalysisLogger:
    """
    Comprehensive logger for analysis pipeline with structured output
    Tracks: stages, models, tokens, costs, timing, errors, quality metrics
    """

    def __init__(self, submission_id: int, company: str):
        self.submission_id = submission_id
        self.company = company
        self.stages = []
        self.start_time = time.time()
        self.total_cost = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def log_stage_start(self, stage_name: str, model: str, task_description: str):
        """Log the start of a pipeline stage"""
        stage_data = {
            "stage": stage_name,
            "model": model,
            "task": task_description,
            "status": "started",
            "start_time": datetime.utcnow().isoformat(),
            "submission_id": self.submission_id,
            "company": self.company
        }

        logger.info(
            f"[STAGE START] {stage_name}",
            extra={
                "submission_id": self.submission_id,
                "stage": stage_name,
                "model": model,
                "task": task_description
            }
        )

        self.stages.append(stage_data)
        return stage_data

    def log_stage_complete(
        self,
        stage_name: str,
        duration_seconds: float,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log the completion of a pipeline stage"""

        # Find the stage
        stage_data = next((s for s in self.stages if s["stage"] == stage_name), None)
        if not stage_data:
            logger.warning(f"Stage {stage_name} not found in stages list")
            return

        # Update stage data
        stage_data.update({
            "status": "completed" if success else "failed",
            "end_time": datetime.utcnow().isoformat(),
            "duration_seconds": round(duration_seconds, 3),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(cost, 6),
            "success": success,
            "error": error,
            "metadata": metadata or {}
        })

        # Update totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost

        # Log
        status_emoji = "✅" if success else "❌"
        logger.info(
            f"[STAGE COMPLETE] {status_emoji} {stage_name} - {duration_seconds:.2f}s, {input_tokens + output_tokens} tokens, ${cost:.4f}",
            extra={
                "submission_id": self.submission_id,
                "stage": stage_name,
                "duration": duration_seconds,
                "tokens": input_tokens + output_tokens,
                "cost": cost,
                "success": success
            }
        )

        if error:
            logger.error(
                f"[STAGE ERROR] {stage_name}: {error}",
                extra={
                    "submission_id": self.submission_id,
                    "stage": stage_name,
                    "error": error
                }
            )

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        duration_seconds: float,
        status_code: int,
        success: bool,
        error: Optional[str] = None
    ):
        """Log external API calls (Apify, Perplexity, etc.)"""
        logger.info(
            f"[API CALL] {method} {endpoint} - {status_code} - {duration_seconds:.2f}s",
            extra={
                "submission_id": self.submission_id,
                "endpoint": endpoint,
                "method": method,
                "duration": duration_seconds,
                "status_code": status_code,
                "success": success,
                "error": error
            }
        )

    def log_data_quality(self, quality_metrics: Dict[str, Any]):
        """Log data quality assessment"""
        logger.info(
            f"[DATA QUALITY] {quality_metrics.get('quality_tier', 'unknown')} - {quality_metrics.get('sources_succeeded', 0)}/{quality_metrics.get('sources_succeeded', 0) + quality_metrics.get('sources_failed', 0)} sources",
            extra={
                "submission_id": self.submission_id,
                "quality_metrics": quality_metrics
            }
        )

    def log_cache_hit(self, cache_type: str, cost_saved: float, age_hours: float):
        """Log cache hit"""
        logger.info(
            f"[CACHE HIT] 🎯 {cache_type} - Saved ${cost_saved:.2f} (age: {age_hours:.1f}h)",
            extra={
                "submission_id": self.submission_id,
                "cache_type": cache_type,
                "cost_saved": cost_saved,
                "age_hours": age_hours
            }
        )

    def log_cache_miss(self, cache_type: str):
        """Log cache miss"""
        logger.info(
            f"[CACHE MISS] ❌ {cache_type}",
            extra={
                "submission_id": self.submission_id,
                "cache_type": cache_type
            }
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of entire pipeline execution"""
        total_duration = time.time() - self.start_time

        summary = {
            "submission_id": self.submission_id,
            "company": self.company,
            "total_duration_seconds": round(total_duration, 2),
            "total_cost_usd": round(self.total_cost, 4),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "stages_completed": len([s for s in self.stages if s.get("status") == "completed"]),
            "stages_failed": len([s for s in self.stages if s.get("status") == "failed"]),
            "stages": self.stages,
            "timestamp": datetime.utcnow().isoformat()
        }

        return summary

    def log_summary(self):
        """Log final summary"""
        summary = self.get_summary()

        logger.info(
            f"[PIPELINE COMPLETE] ✅ {self.company} - {summary['total_duration_seconds']:.1f}s, ${summary['total_cost_usd']:.4f}, {summary['total_tokens']} tokens",
            extra={
                "submission_id": self.submission_id,
                "summary": summary
            }
        )

        # Log per-stage breakdown
        logger.info(f"[STAGE BREAKDOWN] Submission {self.submission_id}:")
        for stage in self.stages:
            if stage.get("status") == "completed":
                logger.info(
                    f"  ├─ {stage['stage']}: {stage['duration_seconds']:.2f}s, "
                    f"{stage['total_tokens']} tokens, ${stage['cost_usd']:.4f} ({stage['model']})"
                )
            else:
                logger.info(f"  ├─ {stage['stage']}: {stage['status']}")

        return summary


def log_model_selection(stage: str, task: str, model: str, reason: str):
    """Log model selection reasoning"""
    logger.info(
        f"[MODEL SELECT] {stage} → {model}",
        extra={
            "stage": stage,
            "task": task,
            "model": model,
            "reason": reason
        }
    )


def log_performance_warning(metric: str, value: float, threshold: float, message: str):
    """Log performance warnings"""
    logger.warning(
        f"[PERFORMANCE WARNING] {metric}: {value} (threshold: {threshold}) - {message}",
        extra={
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "message": message
        }
    )


def log_cost_tracking(stage: str, model: str, input_tokens: int, output_tokens: int, cost: float):
    """Detailed cost tracking"""
    logger.info(
        f"[COST] {stage} ({model}): {input_tokens} in + {output_tokens} out = ${cost:.6f}",
        extra={
            "stage": stage,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost
        }
    )


def timed_execution(stage_name: str):
    """Decorator to time function execution and log"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start
                logger.info(
                    f"[TIMING] {stage_name}: {duration:.2f}s",
                    extra={"stage": stage_name, "duration": duration}
                )
                return result
            except Exception as e:
                duration = time.time() - start
                logger.error(
                    f"[TIMING ERROR] {stage_name} failed after {duration:.2f}s: {e}",
                    extra={"stage": stage_name, "duration": duration, "error": str(e)}
                )
                raise
        return wrapper
    return decorator


# Configure logging format
def setup_logging():
    """Setup structured logging for the entire application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Add JSON formatter for structured logs (optional)
    # Uncomment if you want JSON logs for log aggregation services
    # handler = logging.StreamHandler()
    # handler.setFormatter(jsonlogger.JsonFormatter())
    # logger.addHandler(handler)


# Initialize logging on import
setup_logging()
