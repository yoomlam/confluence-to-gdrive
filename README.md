# Confluence-to-GDrive tool

Exports Confluence pages to Google Drive

## Configuration

To enable access to Confluence, populate `.env_local` with the following:
```
ATLASSIAN_API_KEY='...'
ATLASSIAN_USERNAME="...@navapbc.com"
```
- Created via https://id.atlassian.com/manage-profile/security/api-tokens -- [more info](https://developer.atlassian.com/cloud/confluence/using-the-rest-api/#authentication)

To enable writing to a Google Drive folder, create a Google Service account and save the file as `gdrive_service_account.json`.
- Create Google Cloud project
- Enable Google Drive API for the project
- Create credentials for a service account for the project and download the JSON key file
- Share Google Drive folder with the service account's email so that it has write permissions

## Run Streamlit App

Install libraries
```sh
poetry install
```

To run the Streamlit app, run:
```sh
poetry run python -m streamlit run src/streamlit_ui.py
```

## WIP

To run only the (incomplete) API service, run:
```sh
poetry run python src/api.py
```

## For Development in Firebase Studio
Server should run automatically when starting a workspace. To run manually, run:
```sh
./devserver.sh
```

