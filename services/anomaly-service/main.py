import statistics
from fastapi import FastAPI, HTTPException
from schemas import AnomalyRequest, AnomalyResponse, AnomalyDetail, RulesResponse, RuleDetail

app = FastAPI(title="Anomaly Detection Service")

@app.post("/anomaly/detect", response_model=AnomalyResponse)
def detect_anomalies(payload: AnomalyRequest):
    shifts = payload.shifts
    if not shifts:
        raise HTTPException(status_code=400, detail="Shifts array cannot be empty.")

    anomalies = []
    total_shifts = len(shifts)

    # RULE 1: Unusual Deduction (Requires >= 5 shifts)
    if total_shifts >= 5:
        rates = []
        valid_shifts = []
        
        for s in shifts:
            if s.gross_earned > 0:
                rate = (s.platform_deductions / s.gross_earned) * 100
                rates.append(rate)
                valid_shifts.append({"shift": s, "rate": rate})

        if len(rates) >= 2:
            mean_rate = statistics.mean(rates)
            stdev_rate = statistics.stdev(rates) if len(rates) > 1 else 0

            if stdev_rate > 0:
                for item in valid_shifts:
                    s = item["shift"]
                    rate = item["rate"]
                    
                    # Flag if rate is > 2 std dev above mean AND > 5 points above mean
                    if rate > (mean_rate + 2 * stdev_rate) and rate > (mean_rate + 5.0):
                        deviations = round((rate - mean_rate) / stdev_rate, 1)
                        anomalies.append(AnomalyDetail(
                            type="unusual_deduction",
                            severity="high",
                            shift_id=s.id,
                            shift_date=str(s.shift_date),
                            metric={
                                "observed_commission_pct": round(rate, 1),
                                "average_commission_pct": round(mean_rate, 1),
                                "std_deviations_above_mean": deviations
                            },
                            explanation=f"On {s.shift_date}, your platform deduction on {s.platform} was {round(rate, 1)}% of your gross earnings. Your usual average is {round(mean_rate, 1)}%. This is statistically unusual and worth checking with your platform."
                        ))

    # RULE 2: Income Drop (Requires >= 10 shifts)
    if total_shifts >= 10:
        weeks = {}
        for s in shifts:
            year, week, _ = s.shift_date.isocalendar()
            week_key = f"{year}-W{week:02d}"
            weeks[week_key] = weeks.get(week_key, 0) + s.net_received

        sorted_weeks = sorted(weeks.keys())
        # Needs at least 3 weeks of data to compare
        if len(sorted_weeks) >= 3:
            recent_week = sorted_weeks[-1]
            recent_earnings = weeks[recent_week]

            historical_weeks = sorted_weeks[:-1]
            historical_earnings = [weeks[w] for w in historical_weeks]
            hist_mean = statistics.mean(historical_earnings)

            if hist_mean > 0:
                drop_ratio = (hist_mean - recent_earnings) / hist_mean
                if drop_ratio > 0.30:
                    severity = "high" if drop_ratio > 0.50 else "medium"
                    drop_pct = round(drop_ratio * 100)
                    anomalies.append(AnomalyDetail(
                        type="income_drop",
                        severity=severity,
                        shift_id=None,
                        shift_date=None,
                        metric={
                            "recent_week_earnings": round(recent_earnings, 2),
                            "historical_weekly_average": round(hist_mean, 2),
                            "drop_percentage": drop_pct
                        },
                        explanation=f"Your earnings this week (Rs. {int(recent_earnings)}) dropped {drop_pct}% compared to your average weekly earnings of Rs. {int(hist_mean)}. This could indicate reduced shifts, deactivation, or commission changes."
                    ))

    # RULE 3: Hourly Rate Decline (Requires >= 8 shifts)
    if total_shifts >= 8:
        sorted_shifts = sorted(shifts, key=lambda x: x.shift_date)
        recent_shifts = sorted_shifts[-3:]
        older_shifts = sorted_shifts[:-3]

        def get_avg_hourly(shift_list):
            total_net = sum(s.net_received for s in shift_list)
            total_hours = sum(s.hours_worked for s in shift_list)
            if total_hours > 0:
                return total_net / total_hours
            return 0

        recent_rate = get_avg_hourly(recent_shifts)
        historical_rate = get_avg_hourly(older_shifts)

        if historical_rate > 0:
            drop_ratio = (historical_rate - recent_rate) / historical_rate
            if drop_ratio > 0.15:
                drop_pct = round(drop_ratio * 100)
                anomalies.append(AnomalyDetail(
                    type="hourly_rate_decline",
                    severity="medium",
                    shift_id=None,
                    shift_date=None,
                    metric={
                        "recent_hourly_rate": round(recent_rate, 2),
                        "historical_hourly_rate": round(historical_rate, 2),
                        "drop_percentage": drop_pct
                    },
                    explanation=f"Your effective hourly rate declined from Rs. {int(historical_rate)}/hr historically to Rs. {int(recent_rate)}/hr in your recent shifts ({drop_pct}% drop). You may be earning less per hour, check if premium shift availability has changed."
                ))

    # Format Final Output
    anomaly_count = len(anomalies)
    if anomaly_count == 0:
        summary = f"Analyzed {total_shifts} shifts. No unusual patterns detected. Earnings look normal."
    else:
        summary = f"Analyzed {total_shifts} shifts and found {anomaly_count} anomaly. Review the details below."

    return AnomalyResponse(
        worker_id=payload.worker_id,
        total_shifts_analyzed=total_shifts,
        anomalies_found=anomaly_count,
        anomalies=anomalies,
        summary=summary
    )

@app.get("/anomaly/rules", response_model=RulesResponse)
def get_rules():
    """Provides transparency on how the anomaly detection engine works."""
    return RulesResponse(
        rules=[
            RuleDetail(
                name="unusual_deduction",
                description="Flags shifts where platform commission rate is more than 2 standard deviations above the worker's own historical average.",
                minimum_shifts_required=5,
                severity="high",
                what_it_catches="Platform secretly raising commission rates"
            ),
            RuleDetail(
                name="income_drop",
                description="Flags when the most recent week's total earnings dropped more than 30% compared to the worker's average weekly earnings.",
                minimum_shifts_required=10,
                severity="high if drop > 50%, medium if 30-50%",
                what_it_catches="Sudden deactivation, algorithm changes, or major commission hikes"
            ),
            RuleDetail(
                name="hourly_rate_decline",
                description="Flags when the average hourly rate of the 3 most recent shifts dropped more than 15% compared to earlier shifts.",
                minimum_shifts_required=8,
                severity="medium",
                what_it_catches="Platform sending worker on shorter or cheaper jobs"
            )
        ]
    )