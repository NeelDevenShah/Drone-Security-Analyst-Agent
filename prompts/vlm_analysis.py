VLM_ANALYSIS_PROMPT = (
    "Analyze this drone security camera image. Even if the image contains dark regions, low light, or shadows, "
    "examine it carefully to identify any visible elements. Provide a JSON object with the following keys:\n"
    '1. "description": A clear, concise natural language description of the scene from a security perspective (focusing on people, vehicles, perimeter areas, and their activities).\n'
    '2. "objects": A list containing any of these specific categories that are present: "vehicle", "person", "building", "gate", "road", "nature".\n'
    '3. "activity_type": A single category representing the main activity: "vehicle+person" (if both are interacting), "vehicle" (if only vehicles), "person" (if only people), or "empty".\n'
    "Return ONLY the raw JSON object, no Markdown blocks or extra text."
)
