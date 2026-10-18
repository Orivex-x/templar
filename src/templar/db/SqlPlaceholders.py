"""Safe translation of Templar's ``:name`` SQL parameters for DB-API drivers."""

import re


_PARAMETER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_DOLLAR_QUOTE = re.compile(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$")


def named_to_pyformat(sql: str) -> str:
    """Convert real ``:name`` placeholders without rewriting SQL literals.

    PostgreSQL uses colons in casts (``value::jsonb``), and both PostgreSQL and
    MySQL may contain colons in quoted strings/comments. This small scanner
    changes placeholders only in executable SQL text.
    """
    output: list[str] = []
    index = 0
    length = len(sql)
    dollar_delimiter: str | None = None

    while index < length:
        if dollar_delimiter:
            end = sql.find(dollar_delimiter, index)

            if end == -1:
                output.append(sql[index:])
                break

            end += len(dollar_delimiter)
            output.append(sql[index:end])
            index = end
            dollar_delimiter = None

            continue

        char = sql[index]

        if char == "'":
            end = index + 1

            while end < length:
                if sql[end] == "\\" and end + 1 < length:
                    end += 2
                elif sql[end] == "'":
                    end += 2 if end + 1 < length and sql[end + 1] == "'" else 1

                    if end <= length and (end == length or sql[end - 2] != "'"):
                        break
                else:
                    end += 1

            output.append(sql[index:end])
            index = end

            continue

        if char == '"':
            end = index + 1

            while end < length:
                if sql[end] == '"':
                    end += 2 if end + 1 < length and sql[end + 1] == '"' else 1

                    if end <= length and (end == length or sql[end - 2] != '"'):
                        break
                else:
                    end += 1

            output.append(sql[index:end])
            index = end

            continue

        if sql.startswith("--", index):
            end = sql.find("\n", index)
            end = length if end == -1 else end
            output.append(sql[index:end])
            index = end

            continue

        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            end = length if end == -1 else end + 2
            output.append(sql[index:end])
            index = end

            continue

        if char == "$":
            match = _DOLLAR_QUOTE.match(sql, index)

            if match:
                dollar_delimiter = match.group(0)
                output.append(dollar_delimiter)
                index = match.end()

                continue

        if char == ":" and (index == 0 or sql[index - 1] != ":") and (index + 1 == length or sql[index + 1] != ":"):
            match = _PARAMETER.match(sql, index + 1)

            if match:
                name = match.group(0)
                output.append(f"%({name})s")
                index = match.end()

                continue

        output.append(char)
        index += 1

    return "".join(output)
