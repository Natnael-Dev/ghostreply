# fake-test-number fixture
from app import contacts


def test_name_lookup_by_number_lid_and_local_format(contacts_file):
    assert contacts.name_for("+15550100000@c.us") == "Mom"
    assert contacts.name_for("000000000000001@lid") == "Lulu"
    # @lid resolved by the bridge
    assert contacts.name_for(
        "999999999999999@lid", number="+15550100000"
    ) == "Mom"
    assert contacts.name_for("999@c.us") is None


def test_local_and_international_numbers_match(contacts_file):
    contacts_file.write_text('{"Dad": "+15550100000"}', encoding="utf-8")
    assert contacts.name_for("+15550100000@c.us") == "Dad"


def test_missing_or_broken_file_means_no_contacts(contacts_file):
    contacts_file.write_text("not json", encoding="utf-8")
    assert contacts.names() == []


def test_namespaced_id_helpers_and_lookup(contacts_file):
    assert contacts.namespace_id("wa", "123") == "wa:123"
    assert contacts.namespace_id("wa", "wa:123") == "wa:123"
    assert contacts.strip_namespace("wa:123") == "123"
    assert contacts.strip_namespace("tg:456") == "456"
    assert contacts.strip_namespace("plain") == "plain"

    assert contacts.name_for("wa:+15550100000@c.us") == "Mom"
    assert contacts.name_for("wa:000000000000001@lid") == "Lulu"
    assert contacts.name_for(
        "wa:999999999999999@lid", number="wa:+15550100000"
    ) == "Mom"
