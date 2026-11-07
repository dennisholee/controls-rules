// Example Cedar policies for GET /accounts/{id}.
// Copy into policies/*.cedar to switch a service to the Cedar engine.
// JSON rules and Cedar policies cannot be mixed in one bundle.

// The owner may read the account.
permit (
  principal,
  action == Action::"read",
  resource
)
when {
  principal.sub == resource.ownerId
};

// A caller in the account's region may read it.
permit (
  principal,
  action == Action::"read",
  resource
)
when {
  principal.region == resource.region
};
