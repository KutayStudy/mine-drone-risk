import math
from typing import Dict, List
from backend.app.models.sensor import SensorReading
from backend.app.services import thresholds as T
from backend.app.services.grid_service import format_cell_id, get_cell_key
from backend.app.services.risk_service import calculate_risk_score

MIN_ELAPSED_SECONDS = 1.0

# If the sensor did not move much, treat the change as temporal.
# Otherwise, treat it as a spatial gradient observed by a moving drone.
TEMPORAL_MAX_DISTANCE_M = 0.75

# Minimum absolute changes to avoid noise-only alerts.
CH4_MIN_DELTA_PPM = 1_000.0
CO_MIN_DELTA_PPM = 10.0
CO2_MIN_DELTA_PPM = 250.0
O2_MIN_DROP_PERCENT = 0.30

# Spatial-gradient thresholds for moving drone readings.
CH4_GRADIENT_PPM_PER_METER = 500.0
CO_GRADIENT_PPM_PER_METER = 5.0
CO2_GRADIENT_PPM_PER_METER = 100.0
O2_GRADIENT_PERCENT_PER_METER = 0.05

RISK_SCORE_JUMP_THRESHOLD = 20.0

SEVERITY_RANK = {
    "info": 0,
    "watch": 1,
    "warning": 2,
    "danger": 3,
    "critical": 4,
}

def calculate_rate(old_value: float, new_value: float, elapsed_seconds: float) -> float:
    if elapsed_seconds <= 0:
        return 0.0
    return (new_value - old_value) / elapsed_seconds

def calculate_gradient(delta: float, distance_m: float) -> float:
    if distance_m <= 0:
        return 0.0
    return delta / distance_m

def distance_between(previous: SensorReading, current: SensorReading) -> float:
    return math.sqrt(
        (current.position.x - previous.position.x) ** 2
        + (current.position.y - previous.position.y) ** 2
        + (current.position.z - previous.position.z) ** 2
    )

def crossed_up(previous_value: float, current_value: float, threshold: float) -> bool:
    return previous_value < threshold <= current_value

def crossed_down(previous_value: float, current_value: float, threshold: float) -> bool:
    return previous_value >= threshold > current_value

def classify_event_context( previous: SensorReading,current: SensorReading,distance_m: float) -> str:
    previous_cell = get_cell_key(previous.position)
    current_cell = get_cell_key(current.position)

    if previous.source == "esp32" and current.source == "esp32":
        return "temporal_anomaly"

    if distance_m <= TEMPORAL_MAX_DISTANCE_M:
        return "temporal_anomaly"

    if previous_cell == current_cell:
        return "local_spatial_gradient"

    return "spatial_gradient_alert"


def build_event(
    event_type: str,
    event_class: str,
    severity: str,
    metric: str,
    previous: SensorReading,
    current: SensorReading,
    message: str,
    previous_value: float,
    current_value: float,
    delta: float,
    rate_per_second: float,
    gradient_per_meter: float,
    elapsed_seconds: float,
    distance_m: float,
) -> Dict:
    previous_cell_key = get_cell_key(previous.position)
    current_cell_key = get_cell_key(current.position)

    return {
        "type": event_type,
        "class": event_class,
        "severity": severity,
        "metric": metric,
        "drone_id": current.drone_id,
        "source": current.source,
        "timestamp": current.timestamp.isoformat(),
        "previous_cell_id": format_cell_id(previous_cell_key),
        "cell_id": format_cell_id(current_cell_key),
        "previous_position": {
            "x": previous.position.x,
            "y": previous.position.y,
            "z": previous.position.z,
        },
        "position": {
            "x": current.position.x,
            "y": current.position.y,
            "z": current.position.z,
        },
        "message": message,
        "previous_value": round(previous_value, 2),
        "current_value": round(current_value, 2),
        "delta": round(delta, 2),
        "rate_per_second": round(rate_per_second, 4),
        "gradient_per_meter": round(gradient_per_meter, 4),
        "elapsed_seconds": round(elapsed_seconds, 4),
        "distance_m": round(distance_m, 4),
    }


def detect_threshold_crossings(
    previous: SensorReading,
    current: SensorReading,
    event_class: str,
    elapsed_seconds: float,
    distance_m: float,
) -> List[Dict]:
    events: List[Dict] = []

    ch4_delta = current.gas.ch4_ppm - previous.gas.ch4_ppm
    co_delta = current.gas.co_ppm - previous.gas.co_ppm
    co2_delta = current.gas.co2_ppm - previous.gas.co2_ppm
    o2_delta = current.gas.o2_percent - previous.gas.o2_percent

    if crossed_up(previous.gas.ch4_ppm, current.gas.ch4_ppm, T.CH4_MSHA_WITHDRAW_PPM):
        events.append(build_event(
            event_type="methane_withdrawal_threshold_crossed",
            event_class="threshold_crossing",
            severity="danger",
            metric="ch4_ppm",
            previous=previous,
            current=current,
            message="Methane crossed MSHA withdrawal threshold",
            previous_value=previous.gas.ch4_ppm,
            current_value=current.gas.ch4_ppm,
            delta=ch4_delta,
            rate_per_second=calculate_rate(previous.gas.ch4_ppm, current.gas.ch4_ppm, elapsed_seconds),
            gradient_per_meter=calculate_gradient(ch4_delta, distance_m),
            elapsed_seconds=elapsed_seconds,
            distance_m=distance_m,
        ))
    elif crossed_up(previous.gas.ch4_ppm, current.gas.ch4_ppm, T.CH4_MSHA_ACTION_PPM):
        events.append(build_event(
            event_type="methane_action_threshold_crossed",
            event_class="threshold_crossing",
            severity="warning",
            metric="ch4_ppm",
            previous=previous,
            current=current,
            message="Methane crossed MSHA action threshold",
            previous_value=previous.gas.ch4_ppm,
            current_value=current.gas.ch4_ppm,
            delta=ch4_delta,
            rate_per_second=calculate_rate(previous.gas.ch4_ppm, current.gas.ch4_ppm, elapsed_seconds),
            gradient_per_meter=calculate_gradient(ch4_delta, distance_m),
            elapsed_seconds=elapsed_seconds,
            distance_m=distance_m,
        ))

    if crossed_up(previous.gas.co_ppm, current.gas.co_ppm, T.CO_NIOSH_CEILING_PPM):
        events.append(build_event(
            event_type="carbon_monoxide_ceiling_threshold_crossed",
            event_class="threshold_crossing",
            severity="danger",
            metric="co_ppm",
            previous=previous,
            current=current,
            message="Carbon monoxide crossed NIOSH ceiling threshold",
            previous_value=previous.gas.co_ppm,
            current_value=current.gas.co_ppm,
            delta=co_delta,
            rate_per_second=calculate_rate(previous.gas.co_ppm, current.gas.co_ppm, elapsed_seconds),
            gradient_per_meter=calculate_gradient(co_delta, distance_m),
            elapsed_seconds=elapsed_seconds,
            distance_m=distance_m,
        ))
    elif crossed_up(previous.gas.co_ppm, current.gas.co_ppm, T.CO_OSHA_PEL_TWA_PPM):
        events.append(build_event(
            event_type="carbon_monoxide_exposure_threshold_crossed",
            event_class="threshold_crossing",
            severity="warning",
            metric="co_ppm",
            previous=previous,
            current=current,
            message="Carbon monoxide crossed exposure threshold",
            previous_value=previous.gas.co_ppm,
            current_value=current.gas.co_ppm,
            delta=co_delta,
            rate_per_second=calculate_rate(previous.gas.co_ppm, current.gas.co_ppm, elapsed_seconds),
            gradient_per_meter=calculate_gradient(co_delta, distance_m),
            elapsed_seconds=elapsed_seconds,
            distance_m=distance_m,
        ))

    if crossed_up(previous.gas.co2_ppm, current.gas.co2_ppm, T.CO2_MSHA_SHORT_TERM_PPM):
        events.append(build_event(
            event_type="carbon_dioxide_short_term_threshold_crossed",
            event_class="threshold_crossing",
            severity="danger",
            metric="co2_ppm",
            previous=previous,
            current=current,
            message="Carbon dioxide crossed short-term exposure threshold",
            previous_value=previous.gas.co2_ppm,
            current_value=current.gas.co2_ppm,
            delta=co2_delta,
            rate_per_second=calculate_rate(previous.gas.co2_ppm, current.gas.co2_ppm, elapsed_seconds),
            gradient_per_meter=calculate_gradient(co2_delta, distance_m),
            elapsed_seconds=elapsed_seconds,
            distance_m=distance_m,
        ))
    elif crossed_up(previous.gas.co2_ppm, current.gas.co2_ppm, T.CO2_MSHA_MAX_PPM):
        events.append(build_event(
            event_type="carbon_dioxide_exposure_threshold_crossed",
            event_class="threshold_crossing",
            severity="warning",
            metric="co2_ppm",
            previous=previous,
            current=current,
            message="Carbon dioxide crossed exposure threshold",
            previous_value=previous.gas.co2_ppm,
            current_value=current.gas.co2_ppm,
            delta=co2_delta,
            rate_per_second=calculate_rate(previous.gas.co2_ppm, current.gas.co2_ppm, elapsed_seconds),
            gradient_per_meter=calculate_gradient(co2_delta, distance_m),
            elapsed_seconds=elapsed_seconds,
            distance_m=distance_m,
        ))

    if crossed_down(previous.gas.o2_percent, current.gas.o2_percent, T.O2_MIN_SAFE_PERCENT):
        events.append(build_event(
            event_type="oxygen_deficiency_threshold_crossed",
            event_class="threshold_crossing",
            severity="danger",
            metric="o2_percent",
            previous=previous,
            current=current,
            message="Oxygen crossed below minimum safe threshold",
            previous_value=previous.gas.o2_percent,
            current_value=current.gas.o2_percent,
            delta=o2_delta,
            rate_per_second=calculate_rate(previous.gas.o2_percent, current.gas.o2_percent, elapsed_seconds),
            gradient_per_meter=calculate_gradient(o2_delta, distance_m),
            elapsed_seconds=elapsed_seconds,
            distance_m=distance_m,
        ))

    return events


def detect_gradient_events(
    previous: SensorReading,
    current: SensorReading,
    event_class: str,
    elapsed_seconds: float,
    distance_m: float,
) -> List[Dict]:
    events: List[Dict] = []
    is_temporal = event_class == "temporal_anomaly"

    ch4_delta = current.gas.ch4_ppm - previous.gas.ch4_ppm
    co_delta = current.gas.co_ppm - previous.gas.co_ppm
    co2_delta = current.gas.co2_ppm - previous.gas.co2_ppm
    o2_delta = current.gas.o2_percent - previous.gas.o2_percent

    ch4_rate = calculate_rate(previous.gas.ch4_ppm, current.gas.ch4_ppm, elapsed_seconds)
    co_rate = calculate_rate(previous.gas.co_ppm, current.gas.co_ppm, elapsed_seconds)
    co2_rate = calculate_rate(previous.gas.co2_ppm, current.gas.co2_ppm, elapsed_seconds)
    o2_rate = calculate_rate(previous.gas.o2_percent, current.gas.o2_percent, elapsed_seconds)

    ch4_gradient = calculate_gradient(ch4_delta, distance_m)
    co_gradient = calculate_gradient(co_delta, distance_m)
    co2_gradient = calculate_gradient(co2_delta, distance_m)
    o2_gradient = calculate_gradient(o2_delta, distance_m)

    if ch4_delta >= CH4_MIN_DELTA_PPM:
        ch4_temporal_alarm = is_temporal and ch4_rate > T.TREND_RATE_LIMITS["ch4_ppm_per_second"]
        ch4_spatial_alarm = not is_temporal and ch4_gradient > CH4_GRADIENT_PPM_PER_METER

        if ch4_temporal_alarm or ch4_spatial_alarm:
            events.append(build_event(
                event_type="methane_gradient_detected",
                event_class=event_class,
                severity="warning",
                metric="ch4_ppm",
                previous=previous,
                current=current,
                message="Methane increased significantly along the measurement path",
                previous_value=previous.gas.ch4_ppm,
                current_value=current.gas.ch4_ppm,
                delta=ch4_delta,
                rate_per_second=ch4_rate,
                gradient_per_meter=ch4_gradient,
                elapsed_seconds=elapsed_seconds,
                distance_m=distance_m,
            ))

    if co_delta >= CO_MIN_DELTA_PPM:
        co_temporal_alarm = is_temporal and co_rate > T.TREND_RATE_LIMITS["co_ppm_per_second"]
        co_spatial_alarm = not is_temporal and co_gradient > CO_GRADIENT_PPM_PER_METER

        if co_temporal_alarm or co_spatial_alarm:
            events.append(build_event(
                event_type="carbon_monoxide_gradient_detected",
                event_class=event_class,
                severity="warning",
                metric="co_ppm",
                previous=previous,
                current=current,
                message="Carbon monoxide increased significantly along the measurement path",
                previous_value=previous.gas.co_ppm,
                current_value=current.gas.co_ppm,
                delta=co_delta,
                rate_per_second=co_rate,
                gradient_per_meter=co_gradient,
                elapsed_seconds=elapsed_seconds,
                distance_m=distance_m,
            ))

    if co2_delta >= CO2_MIN_DELTA_PPM:
        co2_temporal_alarm = is_temporal and co2_rate > T.TREND_RATE_LIMITS["co2_ppm_per_second"]
        co2_spatial_alarm = not is_temporal and co2_gradient > CO2_GRADIENT_PPM_PER_METER

        if co2_temporal_alarm or co2_spatial_alarm:
            events.append(build_event(
                event_type="carbon_dioxide_gradient_detected",
                event_class=event_class,
                severity="watch",
                metric="co2_ppm",
                previous=previous,
                current=current,
                message="Carbon dioxide increased significantly along the measurement path",
                previous_value=previous.gas.co2_ppm,
                current_value=current.gas.co2_ppm,
                delta=co2_delta,
                rate_per_second=co2_rate,
                gradient_per_meter=co2_gradient,
                elapsed_seconds=elapsed_seconds,
                distance_m=distance_m,
            ))

    o2_drop = previous.gas.o2_percent - current.gas.o2_percent
    o2_drop_gradient = calculate_gradient(o2_drop, distance_m)

    if o2_drop >= O2_MIN_DROP_PERCENT:
        o2_temporal_alarm = is_temporal and o2_rate < T.TREND_RATE_LIMITS["o2_percent_per_second"]
        o2_spatial_alarm = not is_temporal and o2_drop_gradient > O2_GRADIENT_PERCENT_PER_METER

        if o2_temporal_alarm or o2_spatial_alarm:
            events.append(build_event(
                event_type="oxygen_drop_gradient_detected",
                event_class=event_class,
                severity="danger",
                metric="o2_percent",
                previous=previous,
                current=current,
                message="Oxygen decreased significantly along the measurement path",
                previous_value=previous.gas.o2_percent,
                current_value=current.gas.o2_percent,
                delta=o2_delta,
                rate_per_second=o2_rate,
                gradient_per_meter=o2_gradient,
                elapsed_seconds=elapsed_seconds,
                distance_m=distance_m,
            ))

    return events


def detect_risk_transition(
    previous: SensorReading,
    current: SensorReading,
    event_class: str,
    elapsed_seconds: float,
    distance_m: float,
) -> List[Dict]:
    previous_risk = calculate_risk_score(previous)
    current_risk = calculate_risk_score(current)

    risk_delta = current_risk["risk_score"] - previous_risk["risk_score"]

    if risk_delta < RISK_SCORE_JUMP_THRESHOLD:
        return []

    severity = "danger" if current_risk["alarm_level"] in {"danger", "critical"} else "warning"

    return [
        build_event(
            event_type="risk_score_transition_detected",
            event_class="risk_transition",
            severity=severity,
            metric="risk_score",
            previous=previous,
            current=current,
            message="Risk score increased sharply between consecutive readings",
            previous_value=previous_risk["risk_score"],
            current_value=current_risk["risk_score"],
            delta=risk_delta,
            rate_per_second=risk_delta / elapsed_seconds,
            gradient_per_meter=calculate_gradient(risk_delta, distance_m),
            elapsed_seconds=elapsed_seconds,
            distance_m=distance_m,
        )
    ]


def detect_pair_anomalies(previous: SensorReading, current: SensorReading) -> List[Dict]:
    elapsed_seconds = (current.timestamp - previous.timestamp).total_seconds()

    if elapsed_seconds < MIN_ELAPSED_SECONDS:
        return []

    distance_m = distance_between(previous, current)
    event_class = classify_event_context(previous, current, distance_m)

    events: List[Dict] = []
    events.extend(detect_threshold_crossings(previous, current, event_class, elapsed_seconds, distance_m))
    events.extend(detect_gradient_events(previous, current, event_class, elapsed_seconds, distance_m))
    events.extend(detect_risk_transition(previous, current, event_class, elapsed_seconds, distance_m))

    return events


def detect_anomalies(readings: List[SensorReading]) -> List[Dict]:
    if len(readings) < 2:
        return []

    sorted_readings = sorted(readings, key=lambda reading: reading.timestamp)
    events: List[Dict] = []

    for index in range(1, len(sorted_readings)):
        previous = sorted_readings[index - 1]
        current = sorted_readings[index]

        if previous.drone_id != current.drone_id:
            continue

        events.extend(detect_pair_anomalies(previous, current))

    events = deduplicate_events(events)
    
    events.sort(
        key=lambda event: (
            SEVERITY_RANK.get(event["severity"], 0),
            event["timestamp"],
        ),
        reverse=True,
    )

    return events

def deduplicate_events(events: List[Dict]) -> List[Dict]:
    """
    Keeps the most informative event when multiple events describe the same
    metric transition.

    Priority:
    threshold_crossing > risk_transition > temporal/spatial gradient
    """
    priority = {
        "threshold_crossing": 4,
        "risk_transition": 3,
        "temporal_anomaly": 2,
        "local_spatial_gradient": 2,
        "spatial_gradient_alert": 2,
    }

    best_events: Dict[tuple, Dict] = {}

    for event in events:
        key = (
            event["timestamp"],
            event["metric"],
            event["previous_cell_id"],
            event["cell_id"],
        )

        current_best = best_events.get(key)

        if current_best is None:
            best_events[key] = event
            continue

        event_priority = priority.get(event["class"], 0)
        best_priority = priority.get(current_best["class"], 0)

        if event_priority > best_priority:
            best_events[key] = event

    return list(best_events.values())