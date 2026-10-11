function identity=mamyshev_source_identity(root,identity)
% Produce/check explicit source-byte identity; never consumes physical RNG.
if nargin<2
    listing=dir(fullfile(root,'code','**','*'));
    paths={};
    for k=1:numel(listing)
        if listing(k).isdir, continue; end
        [~,~,extension]=fileparts(listing(k).name);
        if any(strcmp(extension,{'.m','.txt','.mat','.cu','.ptx','.json'}))
            path=fullfile(listing(k).folder,listing(k).name);
            paths{end+1}=path(numel(root)+2:end); %#ok<AGROW>
        end
    end
    paths=sort(paths);
    files=struct('path',{},'sha256',{});
    for k=1:numel(paths)
        files(k)=struct('path',paths{k},'sha256',hash_file(fullfile(root,paths{k})));
    end
    identity=struct('digest',hash_bytes(unicode2native(jsonencode(files),'UTF-8')), ...
        'files',files,'identity_scope','local_preflight_code_and_physical_data');
else
    assert(isstruct(identity) && isfield(identity,'digest') && ...
        isfield(identity,'files') && ~isempty(identity.files), ...
        'Mamyshev:SourceIdentity','Source manifest missing.');
    for k=1:numel(identity.files)
        entry=identity.files(k);
        assert(~startsWith(entry.path,'/') && ~contains(entry.path,'..') && ...
            strcmp(hash_file(fullfile(root,entry.path)),entry.sha256), ...
            'Mamyshev:SourceIdentity','Source hash mismatch: %s.',entry.path);
    end
end
end

function value=hash_file(path)
fid=fopen(path,'rb'); assert(fid>=0,'Mamyshev:SourceIdentity','Cannot read %s.',path);
cleanup=onCleanup(@()fclose(fid)); %#ok<NASGU>
value=hash_bytes(fread(fid,Inf,'*uint8'));
end
function value=hash_bytes(bytes)
digest=java.security.MessageDigest.getInstance('SHA-256');
digest.update(bytes);
value=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2).',1,[]));
end
