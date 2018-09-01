from applicationinsights import TelemetryClient


telemetry_client = TelemetryClient('0d21236a-e9fc-447d-910b-359ceda2fac5')

def log_case_not_found(case_citation):
    telemetry_client.track_event('Case Not Found', {'Citation': case_citation})
    telemetry_client.flush()


def log_successful_download(case_citation):
    telemetry_client.track_event('PDF Downloaded', {'Citation': case_citation})
    telemetry_client.flush()

def log_new_session(username, search_count):
    telemetry_client.track_event('Session Opened', {'User': username, 'Search Count': search_count})
    telemetry_client.flush()
