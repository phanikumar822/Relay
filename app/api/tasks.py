import uuid
import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from app.database.mongo import tasks_col, events_col, MongoUser
from app.api.deps import get_current_user
from app.graph.workflow import event_discovery_graph
from app.services.mailer import send_event_digest

logger = logging.getLogger("agent.tasks")

task_router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

class PromptRequest(BaseModel):
    prompt: str
    mode: Optional[str] = "immediate"
    target_day: Optional[str] = None
    daily_run_minutes: Optional[int] = 60

def parse_target_date(target_day_str: Optional[str]) -> date:
    today = datetime.utcnow().date()
    if not target_day_str:
        return today
    target_clean = target_day_str.strip().lower()
    # Try YYYY-MM-DD
    try:
        return datetime.strptime(target_clean, "%Y-%m-%d").date()
    except ValueError:
        pass

    # Try day of week (e.g. monday, tuesday, etc.)
    days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for idx, day_name in enumerate(days_of_week):
        if day_name in target_clean:
            today_idx = today.weekday()
            days_ahead = (idx - today_idx) % 7
            if days_ahead == 0:
                days_ahead = 7  # Next week if specified today
            return today + timedelta(days=days_ahead)

    # Fallback to today if unparseable
    return today

async def run_immediate_pipeline(task_id: str, prompt: str, user_email: str):
    t_col = tasks_col()
    e_col = events_col()
    
    task = await t_col.find_one({"_id": task_id})
    if not task:
        return

    await t_col.update_one({"_id": task_id}, {"$set": {"status": "RUNNING"}})

    try:
        initial_state = {
            "task_id": task_id,
            "raw_prompt": prompt,
            "current_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "criteria": {},
            "scraped_events": [],
            "verified_events": [],
            "ranked_events": []
        }
        final_state = await event_discovery_graph.ainvoke(initial_state)
        ranked = final_state.get("ranked_events", [])
        criteria = final_state.get("criteria", {})
        delay_minutes = criteria.get("delay_minutes", 0)

        # If user requested a delay in prompt, wait before dispatching
        if delay_minutes and delay_minutes > 0:
            logger.info("Task %s: User requested %d minute delay. Waiting before email delivery...", task_id, delay_minutes)
            await t_col.update_one({"_id": task_id}, {"$set": {"status": f"WAITING (Delivering in {delay_minutes}m)"}})
            await asyncio.sleep(delay_minutes * 60)
            await t_col.update_one({"_id": task_id}, {"$set": {"status": "RUNNING"}})

        fresh_events = []
        for event in ranked:
            url = event.get("url")
            if not url:
                continue
            exists = await e_col.find_one({"event_url": url})
            if not exists:
                fresh_events.append(event)
                await e_col.insert_one({
                    "_id": str(uuid.uuid4()),
                    "event_url": url,
                    "title": event.get("title", ""),
                    "platform": event.get("platform", "Web"),
                    "event_date": event.get("date", ""),
                    "priority": event.get("priority", "MEDIUM"),
                    "first_seen_at": datetime.utcnow()
                })

        email_dispatched = False
        email_error = None
        if fresh_events:
            try:
                username = user_email.split("@")[0]
                await send_event_digest(user_email, fresh_events, username=username)
                email_dispatched = True
            except Exception as mail_err:
                logger.warning("Task %s: Email dispatch skipped or timed out (%s). Events saved to UI.", task_id, mail_err)
                email_dispatched = False
                email_error = str(mail_err)

        await t_col.update_one(
            {"_id": task_id},
            {"$set": {
                "status": "COMPLETED",
                "email_dispatched": email_dispatched,
                "email_error": email_error,
                "result_summary": fresh_events
            }}
        )

    except Exception as e:
        logger.error("Task %s failed: %s", task_id, e)
        await t_col.update_one(
            {"_id": task_id},
            {"$set": {
                "status": "FAILED",
                "result_summary": {"error": str(e)}
            }}
        )

async def run_scheduled_pipeline(
    task_id: str,
    prompt: str,
    user_email: str,
    target_day_str: Optional[str],
    daily_run_minutes: int
):
    t_col = tasks_col()
    e_col = events_col()

    task = await t_col.find_one({"_id": task_id})
    if not task:
        return

    target_date = parse_target_date(target_day_str)
    current_date = datetime.utcnow().date()
    if target_date < current_date:
        target_date = current_date

    # Enforce cap at 60 minutes
    capped_run_mins = min(max(1, daily_run_minutes), 60)
    # T_sleep formula: 24 hours - T_run (in seconds)
    t_sleep_seconds = ((24 * 60) - capped_run_mins) * 60
    sleep_hours = (24 * 60 - capped_run_mins) / 60.0

    all_fresh_events = []
    day_count = 1

    try:
        while current_date <= target_date:
            cycle_label = f"Day {day_count} ({current_date.strftime('%Y-%m-%d')})"
            logger.info("Task %s: Scheduled search cycle %s starting. Target: %s. T_run: %dm", task_id, cycle_label, target_date, capped_run_mins)
            
            await t_col.update_one(
                {"_id": task_id},
                {"$set": {
                    "status": f"RUNNING ({cycle_label})",
                    "current_cycle_date": current_date.strftime("%Y-%m-%d"),
                    "target_date": target_date.strftime("%Y-%m-%d")
                }}
            )

            initial_state = {
                "task_id": task_id,
                "raw_prompt": prompt,
                "current_date": current_date.strftime("%Y-%m-%d"),
                "criteria": {},
                "scraped_events": [],
                "verified_events": [],
                "ranked_events": []
            }

            final_state = await event_discovery_graph.ainvoke(initial_state)
            ranked = final_state.get("ranked_events", [])

            for event in ranked:
                url = event.get("url")
                if not url:
                    continue
                exists = await e_col.find_one({"event_url": url})
                if not exists:
                    all_fresh_events.append(event)
                    await e_col.insert_one({
                        "_id": str(uuid.uuid4()),
                        "event_url": url,
                        "title": event.get("title", ""),
                        "platform": event.get("platform", "Web"),
                        "event_date": event.get("date", ""),
                        "priority": event.get("priority", "MEDIUM"),
                        "first_seen_at": datetime.utcnow()
                    })

            await t_col.update_one(
                {"_id": task_id},
                {"$set": {
                    "result_summary": all_fresh_events,
                    "last_run_at": datetime.utcnow()
                }}
            )

            # Check if target date is reached
            if current_date >= target_date:
                logger.info("Task %s: Reached target day %s. Concluding multi-day schedule.", task_id, target_date)
                break

            # T_sleep = 24 hours - T_run pause before next day cycle
            pause_status = f"PAUSED (Sleeping {sleep_hours:.1f}h until next cycle)"
            logger.info("Task %s: Completed %s. Sleeping %0.1f hours (%ds) until next daily run.", task_id, cycle_label, sleep_hours, t_sleep_seconds)
            
            await t_col.update_one(
                {"_id": task_id},
                {"$set": {"status": pause_status}}
            )

            await asyncio.sleep(t_sleep_seconds)

            current_date += timedelta(days=1)
            day_count += 1

        # Final multi-day dispatch
        email_dispatched = False
        email_error = None
        if all_fresh_events:
            try:
                username = user_email.split("@")[0]
                await send_event_digest(user_email, all_fresh_events, username=username)
                email_dispatched = True
            except Exception as mail_err:
                logger.warning("Scheduled Task %s: Email dispatch skipped or timed out (%s). Events saved to UI.", task_id, mail_err)
                email_dispatched = False
                email_error = str(mail_err)

        await t_col.update_one(
            {"_id": task_id},
            {"$set": {
                "status": "COMPLETED",
                "email_dispatched": email_dispatched,
                "email_error": email_error,
                "result_summary": all_fresh_events
            }}
        )
        logger.info("Task %s: Multi-day scheduled execution completed. Total events: %d, Email dispatched: %s", task_id, len(all_fresh_events), email_dispatched)

    except Exception as e:
        logger.error("Scheduled Task %s failed: %s", task_id, e)
        await t_col.update_one(
            {"_id": task_id},
            {"$set": {
                "status": "FAILED",
                "result_summary": {"error": str(e)}
            }}
        )

# Backward compatibility alias
run_discovery_pipeline = run_immediate_pipeline

@task_router.post("/run")
async def trigger_task(
    req: PromptRequest,
    bg_tasks: BackgroundTasks,
    current_user: MongoUser = Depends(get_current_user)
):
    mode = req.mode if req.mode in ["immediate", "scheduled"] else "immediate"
    capped_run_mins = min(max(1, req.daily_run_minutes or 60), 60) if req.daily_run_minutes is not None else 60

    new_task_id = str(uuid.uuid4())
    task_doc = {
        "_id": new_task_id,
        "user_id": current_user.id,
        "raw_prompt": req.prompt,
        "mode": mode,
        "target_day": req.target_day if mode == "scheduled" else None,
        "daily_run_minutes": capped_run_mins if mode == "scheduled" else None,
        "status": "QUEUED",
        "email_dispatched": False,
        "result_summary": None,
        "created_at": datetime.utcnow()
    }
    await tasks_col().insert_one(task_doc)

    if mode == "scheduled":
        bg_tasks.add_task(
            run_scheduled_pipeline,
            new_task_id,
            req.prompt,
            current_user.email,
            req.target_day,
            capped_run_mins
        )
        msg = f"Multi-day scheduled task queued (Target: {req.target_day}, Daily duration: {capped_run_mins}m). Daily cycles will run in background."
    else:
        bg_tasks.add_task(
            run_immediate_pipeline,
            new_task_id,
            req.prompt,
            current_user.email
        )
        msg = "Immediate task queued. Verification, scraping, and ranking running in background."

    return {
        "task_id": new_task_id,
        "mode": mode,
        "status": "QUEUED",
        "message": msg
    }

@task_router.get("/history")
async def get_history(current_user: MongoUser = Depends(get_current_user)):
    cursor = tasks_col().find({"user_id": current_user.id}).sort("created_at", -1)
    tasks = await cursor.to_list(length=100)
    return [{
        "task_id": t["_id"],
        "prompt": t.get("raw_prompt", ""),
        "mode": t.get("mode", "immediate"),
        "target_day": t.get("target_day"),
        "daily_run_minutes": t.get("daily_run_minutes"),
        "status": t.get("status", "UNKNOWN"),
        "email_dispatched": t.get("email_dispatched", False),
        "email_error": t.get("email_error"),
        "results": t.get("result_summary"),
        "created_at": t.get("created_at").isoformat() if t.get("created_at") else None
    } for t in tasks]
