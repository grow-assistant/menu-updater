# Response Personalization Features

## Overview

The personalization system allows SWOOP AI to tailor responses to individual users based on their usage patterns, preferences, and behavior. This document explains the personalization features and their implementation.

## Key Components

### 1. UserProfile Class

The `UserProfile` class in `services/context_manager.py` is the core component that tracks user-specific information, including:

- **Usage statistics**: Query counts, category distribution, time-of-day patterns
- **Entity tracking**: Frequently referenced menu items, categories, and other entities
- **Topic tracking**: Preferred topics and topic transitions
- **Personalization preferences**: Response detail level, tone, etc.
- **Session tracking**: Session duration and frequency

### 2. Personalization Context

The personalization context is derived from the `UserProfile` and provides the following information to response generators:

- **Response preferences**: Detail level and tone settings
- **Frequently accessed entities**: Common items/categories the user references
- **Expertise level**: Inferred from usage patterns
- **Time patterns**: User's preferred time periods and day patterns
- **Session context**: Recent queries and current focus

### 3. Response Generator Integration

The `ResponseGenerator` service uses personalization hints to customize responses in several ways:

- **Detail level adjustment**: Concise vs. detailed responses based on user preference
- **Tone adaptation**: Formal, professional, casual, or friendly tone
- **Entity references**: Highlighting entities the user frequently queries
- **Terminology adaptation**: Based on inferred expertise level

## Personalization Flow

1. The Query Processor receives a query with a user ID
2. The Context Manager retrieves or creates a `UserProfile` for that user
3. The user's query is processed and relevant profile information is updated
4. When generating a response, personalization hints are extracted from the profile
5. The Response Generator uses these hints to tailor the response format and content

## Example Use Cases

### Detail Level Personalization

For users who prefer concise responses:
```
"You sold 120 burgers last month, up 15% from the previous month."
```

For users who prefer detailed responses:
```
"Last month, your restaurant sold 120 burgers, which represents a 15% increase from the 105 burgers sold in the previous month. This item continues to be in your top 3 selling products, with consistent growth over the past quarter."
```

### Tone Adaptation

Professional tone:
```
"The data indicates a 12% revenue increase in the dessert category during the last quarter."
```

Friendly tone:
```
"Great news! Your dessert sales are up 12% this quarter - looks like those new cheesecake flavors are a hit!"
```

## User Preference Settings

Users can explicitly set preferences through commands:

- `"Please give me more detailed responses"` → Sets detail_level to "detailed"
- `"I prefer concise answers"` → Sets detail_level to "concise"
- `"Use a more casual tone"` → Sets response_tone to "casual"

## Implementation Details

### Pattern Analysis

The UserProfile periodically analyzes query patterns to detect:

- Preferred time of day for specific query types
- Recurring entity interests (e.g., frequently checking specific menu items)
- Topic focus patterns (e.g., predominantly interested in sales data)

### Entity Tracking

Entities are tracked with a counter system:
```python
self.frequent_entities["menu_items:burger"] += 1
```

The most commonly referenced entities are made available to the response generator.

### Session Metrics

Each user session is tracked for duration and interaction patterns:
```python
def start_session(self):
    self.stats["total_sessions"] += 1
    self.session_start_time = datetime.now()

def end_session(self):
    if hasattr(self, 'session_start_time'):
        session_duration = (datetime.now() - self.session_start_time).total_seconds()
        self.stats["total_time_spent"] += session_duration
        # Update average session length
        # ...
```

## Future Enhancements

1. **Learning user vocabulary**: Adapting to the specific terminology a user prefers
2. **Time-based preferences**: Tailoring response detail based on time of day
3. **Visual preferences**: Learning user preferences for charts vs. tables
4. **Proactive suggestions**: Offering suggestions based on frequent query patterns
5. **Adaptive clarification**: Adjusting clarification strategies based on user behavior 