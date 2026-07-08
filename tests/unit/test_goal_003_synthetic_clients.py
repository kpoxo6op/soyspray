import yaml

from scripts.synthetic_bank_config import AUTH_PROFILE, AUTH_STATE, AUTHORIZATION_PROFILE, CLIENTS, ROOT, RUNTIME_CREDENTIAL_SOURCE


def test_all_synthetic_clients_exist_and_do_not_create_credentials():
    catalog = yaml.safe_load((ROOT / "clients/synthetic/client-catalog.yaml").read_text(encoding="utf-8"))
    clients = {client["client_name"]: client for client in catalog["clients"]}
    assert set(clients) == set(CLIENTS)
    for name, client in clients.items():
        assert (ROOT / "clients/synthetic" / f"{name}.yaml").is_file()
        assert client["credentials_created"] == RUNTIME_CREDENTIAL_SOURCE
        assert client["current_auth_state"] == AUTH_STATE
        assert client["auth_profile"] == AUTH_PROFILE
        assert client["authorization_profile"] == AUTHORIZATION_PROFILE
        assert client["credential_secret_namespace"] == "synthetic-clients"
        assert client["data_classification"] == "synthetic"
