import yaml

from scripts.synthetic_bank_config import CLIENTS, ROOT


def test_all_synthetic_clients_exist_and_do_not_create_credentials():
    catalog = yaml.safe_load((ROOT / "clients/synthetic/client-catalog.yaml").read_text(encoding="utf-8"))
    clients = {client["client_name"]: client for client in catalog["clients"]}
    assert set(clients) == set(CLIENTS)
    for name, client in clients.items():
        assert (ROOT / "clients/synthetic" / f"{name}.yaml").is_file()
        assert client["credentials_created"] is False
        assert client["current_auth_state"] == "temporary-no-auth"
        assert client["data_classification"] == "synthetic"
        assert client["future_auth_profile"] == "goal-004-auth-rate-limit-security"
