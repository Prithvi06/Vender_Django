from os import path

TEST_FILE_FOLDER = path.join("apps", "vendor", "tests")


def _mock_download_ofac_alternate_file(*args, **kwargs) -> list[str]:
    filename = path.join(TEST_FILE_FOLDER, "ALT.csv")
    with open(filename) as file:
        lines = file.readlines()
    return lines


def _mock_download_ofac_address_file(*args, **kwargs) -> list[str]:
    filename = path.join(TEST_FILE_FOLDER, "ADD.csv")
    with open(filename) as file:
        lines = file.readlines()
    return lines


def _mock_download_ofac_sdn_file(*args, **kwargs) -> list[str]:
    filename = path.join(TEST_FILE_FOLDER, "SDN.csv")
    with open(filename) as file:
        lines = file.readlines()
    return lines
