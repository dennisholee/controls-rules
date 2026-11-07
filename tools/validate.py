#!/usr/bin/env python3
"""Validate the delivery-owned controls configuration.

Stdlib only, so it runs anywhere Python 3 runs. This is a local pre-check; the
pipeline performs the full JSON Schema, OpenAPI-diff and conformance gates.
"""

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCKED = {"ssn", "pan", "cvv", "cardNumber"}
VALID_MODES = {"none", "full", "partial"}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

errors = []


def rel(path):
    return os.path.relpath(path, ROOT)


def load(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        errors.append("%s: %s" % (rel(path), exc))
        return None


def collect(pattern):
    return sorted(glob.glob(os.path.join(ROOT, pattern)))


def check_policies():
    rule_ids = set()
    count = 0
    for path in collect("policies/*.json"):
        doc = load(path)
        if doc is None:
            continue
        if doc.get("defaultEffect") not in ("deny", "allow"):
            errors.append("%s: defaultEffect must be deny or allow" % rel(path))
        if doc.get("engine") == "opa" and doc.get("rules"):
            errors.append("%s: engine opa cannot include JSON rules" % rel(path))
        for rule in doc.get("rules", []):
            count += 1
            rid = rule.get("id", "")
            if not rid:
                errors.append("%s: rule without id" % rel(path))
                continue
            if rid in rule_ids:
                errors.append("%s: duplicate rule id %s" % (rel(path), rid))
            rule_ids.add(rid)
            if rule.get("effect") not in ("allow", "deny"):
                errors.append("%s: rule %s effect invalid" % (rel(path), rid))
            if not rule.get("when"):
                errors.append("%s: rule %s has no condition" % (rel(path), rid))
    cedar = collect("policies/*.cedar")
    if cedar and count:
        errors.append("cannot combine JSON rules with Cedar policies")
    if cedar:
        print("cedar policies: %d files" % len(cedar))
    print("policies: %d rules" % count)


def check_masks():
    names = set()
    count = 0
    for path in collect("mask-policies/*.json"):
        doc = load(path)
        if doc is None:
            continue
        for name, policy in doc.get("policies", {}).items():
            count += 1
            if name in names:
                errors.append("%s: duplicate policy %s" % (rel(path), name))
            names.add(name)
            if policy.get("default", "none") not in ("none", "full"):
                errors.append("%s: %s default invalid" % (rel(path), name))
            for field, spec in policy.get("fields", {}).items():
                mode = spec.get("mode")
                if mode not in VALID_MODES:
                    errors.append("%s: %s.%s mode invalid" % (rel(path), name, field))
                last = field.split(".")[-1].replace("[*]", "")
                if last in LOCKED and mode != "full":
                    errors.append(
                        "%s: %s.%s is locked and must be full" % (rel(path), name, field)
                    )
                if mode == "partial" and not any(
                    k in spec for k in ("keepPrefix", "keepSuffix", "preserveDomain", "keep")
                ):
                    errors.append(
                        "%s: %s.%s partial requires explicit parameters"
                        % (rel(path), name, field)
                    )
            for field in policy.get("rejectFields", []):
                if not isinstance(field, str) or not field:
                    errors.append("%s: %s rejectFields invalid" % (rel(path), name))
    print("mask policies: %d" % count)
    return names


def check_registry(mask_names):
    endpoint_ids = set()
    count = 0
    for path in collect("registry/*.json"):
        doc = load(path)
        if doc is None:
            continue
        unregistered = doc.get("defaultUnregistered", "deny")
        if unregistered != "deny":
            errors.append(
                "%s: defaultUnregistered must be deny (got %s)" % (rel(path), unregistered)
            )
        for ep in doc.get("endpoints", []):
            count += 1
            eid = ep.get("id", "")
            if not eid:
                errors.append("%s: endpoint without id" % rel(path))
                continue
            if eid in endpoint_ids:
                errors.append("%s: duplicate endpoint id %s" % (rel(path), eid))
            endpoint_ids.add(eid)
            if not ID_RE.match(eid):
                errors.append("%s: endpoint id %s is not kebab-case" % (rel(path), eid))
            for key in ("method", "path", "resourceType"):
                if not ep.get(key):
                    errors.append("%s: endpoint %s missing %s" % (rel(path), eid, key))
            service = ep.get("service")
            if not service:
                errors.append("%s: endpoint %s missing service" % (rel(path), eid))
            elif not ID_RE.match(service):
                errors.append("%s: endpoint %s service not kebab-case" % (rel(path), eid))
            ref = ep.get("resourceId", {})
            if ref.get("from") == "path" and not ref.get("name"):
                errors.append("%s: endpoint %s path ref needs name" % (rel(path), eid))
            if ref.get("from") == "body" and not ref.get("path", "").startswith("$."):
                errors.append("%s: endpoint %s body ref needs $.path" % (rel(path), eid))
            mask = ep.get("maskPolicy")
            if mask and mask not in mask_names:
                errors.append("%s: endpoint %s unknown maskPolicy %s" % (rel(path), eid, mask))
            if ep.get("selfDescribing") and ref.get("from") != "body":
                errors.append(
                    "%s: endpoint %s selfDescribing requires body resourceId"
                    % (rel(path), eid)
                )
    print("registry: %d endpoints" % count)


def check_dq():
    ids = set()
    count = 0
    for path in collect("dq/*.json"):
        doc = load(path)
        if doc is None:
            continue
        for rule in doc.get("rules", []):
            count += 1
            rid = rule.get("id", "")
            if not rid:
                errors.append("%s: dq rule without id" % rel(path))
                continue
            if rid in ids:
                errors.append("%s: duplicate dq rule %s" % (rel(path), rid))
            ids.add(rid)
            if not rule.get("field"):
                errors.append("%s: dq rule %s missing field" % (rel(path), rid))
    print("dq: %d rules" % count)


def check_service_overlays():
    for path in collect("services/*/overrides.json"):
        doc = load(path)
        if doc is None:
            continue
        bundle = doc.get("bundle") or {}
        if bundle.get("defaultUnregistered") == "allow":
            errors.append("%s: bundle.defaultUnregistered may not be allow" % rel(path))
        service = doc.get("service")
        expected = rel(path).split(os.sep)[1]
        if service and service != expected:
            errors.append("%s: service %r does not match directory" % (rel(path), service))


def check_env():
    for path in collect("env/*/overrides.json"):
        doc = load(path)
        if doc is None:
            continue
        if doc.get("defaultUnregistered") == "allow":
            errors.append("%s: production guardrail violated" % rel(path))
        bundle = doc.get("bundle") or {}
        if bundle.get("defaultUnregistered") == "allow":
            errors.append("%s: bundle.defaultUnregistered may not be allow" % rel(path))
        env = doc.get("environment")
        expected = rel(path).split(os.sep)[1]
        if env != expected:
            errors.append("%s: environment %r does not match directory" % (rel(path), env))


def check_fixtures():
    count = 0
    for path in collect("tests/fixtures/*.json"):
        doc = load(path)
        if doc is None:
            continue
        count += 1
        for key in ("name", "request", "expect", "service"):
            if key not in doc:
                errors.append("%s: fixture missing %s" % (rel(path), key))
        if doc.get("request", {}).get("method") is None:
            errors.append("%s: fixture request missing method" % rel(path))
    print("fixtures: %d" % count)


def main():
    masks = check_masks()
    check_policies()
    check_registry(masks)
    check_dq()
    check_env()
    check_service_overlays()
    check_fixtures()
    if errors:
        print("\nFAILED (%d):" % len(errors))
        for err in errors:
            print("  - " + err)
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
