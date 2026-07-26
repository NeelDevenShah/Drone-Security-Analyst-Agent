ALERT_ENRICHMENT_PROMPT = (
    "<|im_start|>system\n"
    "You are a drone security analyst. Write a single clear, factual alert message "
    "(1-2 sentences, no speculation) for the following confirmed security event.<|im_end|>\n"
    "<|im_start|>user\n"
    "Alert type: {alert_type}\n"
    "Location: {location}\n"
    "Timestamp: {timestamp}\n"
    "VLM description: {description}\n"
    "Detected objects: {objects}\n"
    "Activity: {activity}\n"
    "Write only the alert message text.<|im_end|>\n"
    "<|im_start|>assistant\n"
)
