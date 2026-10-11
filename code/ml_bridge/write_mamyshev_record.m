function write_mamyshev_record(path, record)
%WRITE_MAMYSHEV_RECORD Actual JSON serialization path, including null + reason.
% Refuse accidental overwrite of existing evidence. No raw waveforms serialized.
assert(strcmp(record.result_protocol_version,'safe_result_v1'), ...
    'MamyshevRecord:UnknownProtocol','Unexpected record protocol.');
assert(~isfile(path),'MamyshevRecord:ExistingRecord','Refusing to overwrite %s.',path);
parent = fileparts(path);
if isempty(parent), parent = pwd; end
assert(isfolder(parent),'MamyshevRecord:WriteError','Record directory does not exist: %s.',parent);
mamyshev_write_diagnostic(path,record,false);
end
