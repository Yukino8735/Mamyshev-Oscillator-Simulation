function mamyshev_write_diagnostic(path,value,replace_existing)
% Atomic diagnostic JSON; deterministic process-local names never use RNG.
if nargin<3, replace_existing=false; end
assert(replace_existing || ~isfile(path),'MamyshevRecord:ExistingRecord', ...
    'Refusing to overwrite %s.',path);
parent=fileparts(path); if isempty(parent), parent=pwd; end
assert(isfolder(parent),'MamyshevRecord:WriteError','Missing record directory.');
persistent serial
if isempty(serial), serial=0; end
serial=serial+1;
temporary=sprintf('%s.tmp-%d-%d',path,feature('getpid'),serial);
assert(~isfile(temporary),'MamyshevRecord:WriteError','Temporary path already exists.');
cleanup=onCleanup(@()remove_temporary(temporary)); %#ok<NASGU>
payload=[jsonencode(value,'ConvertInfAndNaN',true) newline];
fid=fopen(temporary,'w');
assert(fid>=0,'MamyshevRecord:WriteError','Cannot create diagnostic temporary file.');
try
    written=fprintf(fid,'%s',payload);
    close_status=fclose(fid); fid=-1;
    assert(written==numel(unicode2native(payload,'UTF-8')) && close_status==0, ...
        'MamyshevRecord:WriteError','Incomplete diagnostic write.');
catch exception
    if fid>=0, fclose(fid); end
    rethrow(exception);
end
assert(replace_existing || ~isfile(path),'MamyshevRecord:ExistingRecord','Record now exists.');
[ok,message]=movefile(temporary,path);
assert(ok,'MamyshevRecord:WriteError','%s',message);
end

function remove_temporary(path)
if isfile(path), delete(path); end
end
