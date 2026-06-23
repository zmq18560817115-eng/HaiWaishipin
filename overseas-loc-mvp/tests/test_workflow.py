import unittest

from app.workflow import (
    FORBIDDEN_TERMS,
    build_validation_retry_message,
    generate_srt,
    validate_localization,
)


VALID_MARKDOWN = """# EN Localization Pack

## 1. Video structure

| Segment | Time |
|---|---|
| Hook | 0–3s |

## 2. Subtitles by shot

### Shot 1
- **EN**: Make night pumping fit a calmer routine.
### Shot 2
- **EN**: Keep your essentials ready for every session.
### Shot 3
- **EN**: Adjust the settings to match your routine.
### Shot 4
- **EN**: Easy to clean parts simplify the reset.
### Shot 5
- **EN**: Pack your pump and keep moving confidently.

## 3. Hook variants

| # | Theme | Hook |
|---|---|---|
| 1 | night | A calmer night routine |
| 2 | work | Pack for the workday |
| 3 | fit | Find your flange size |
| 4 | clean | Simplify the next reset |
| 5 | portable | Take your routine along |

## 4. Cover titles

1. A Calmer Night Routine
2. Ready for the Workday
3. Pack and Keep Moving

## 5. Allowed claims used

- portable design
- easy to clean parts

## 6. Compliance checklist

- [x] Checked

## 7. Revision log

| Date | Version |
|---|---|
| 2026-06-22 | test |
"""


class WorkflowTests(unittest.TestCase):
    def test_valid_output_and_srt(self):
        result = validate_localization(
            VALID_MARKDOWN,
            ["portable design", "easy to clean parts"],
            FORBIDDEN_TERMS,
        )
        self.assertTrue(result["valid"], result["errors"])
        srt = generate_srt(VALID_MARKDOWN)
        self.assertIn("00:00:17,000 --> 00:00:18,500", srt)
        self.assertIn("00:00:18,500 --> 00:00:20,000", srt)
        self.assertIn("Pack your pump and keep moving", srt)
        self.assertIn("confidently.", srt)

    def test_forbidden_term_fails(self):
        invalid = VALID_MARKDOWN.replace(
            "Make night pumping fit a calmer routine.",
            "This is a pain-free guaranteed routine.",
        )
        result = validate_localization(
            invalid,
            ["portable design", "easy to clean parts"],
            FORBIDDEN_TERMS,
        )
        rules = {item["rule"] for item in result["errors"]}
        self.assertIn("V5", rules)

    def test_retry_message_only_for_v1_v4(self):
        broken_hooks = VALID_MARKDOWN.replace(
            "| 5 | portable | Take your routine along |",
            "",
        )
        validation = validate_localization(
            broken_hooks,
            ["portable design", "easy to clean parts"],
            FORBIDDEN_TERMS,
        )
        self.assertFalse(validation["valid"])
        message = build_validation_retry_message(validation["errors"])
        self.assertIsNotNone(message)
        self.assertIn("V3", message)

        forbidden_only = validate_localization(
            VALID_MARKDOWN.replace(
                "Make night pumping fit a calmer routine.",
                "This is a pain-free guaranteed routine.",
            ),
            ["portable design", "easy to clean parts"],
            FORBIDDEN_TERMS,
        )
        self.assertIsNone(build_validation_retry_message(forbidden_only["errors"]))


if __name__ == "__main__":
    unittest.main()
