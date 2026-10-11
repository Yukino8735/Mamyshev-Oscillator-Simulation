function records=mamyshev_artifact_integrity(output_dir,paths)
% Byte identity for completed diagnostic artifacts; never consumes physical RNG.
% Content validation remains separate: matching hashes do not validate physics.
if nargin<2
    paths={'requested.json','configuration.mat','configuration.json', ...
        'configuration_comparison.json','runtime_calls.json','runtime_observer.json'};
end
records=struct('path',{},'sha256',{},'bytes',{});
for k=1:numel(paths)
    relative=paths{k};
    assert(~startsWith(relative,'/') && ~contains(relative,'..'), ...
        'Mamyshev:ArtifactIntegrity','Artifact path must be relative to this run.');
    fid=fopen(fullfile(output_dir,relative),'rb');
    assert(fid>=0,'Mamyshev:ArtifactIntegrity','Missing completed artifact: %s.',relative);
    cleanup=onCleanup(@()fclose(fid));
    bytes=fread(fid,Inf,'*uint8');
    digest=java.security.MessageDigest.getInstance('SHA-256');
    digest.update(bytes);
    checksum=lower(reshape(dec2hex(typecast(digest.digest(),'uint8'),2).',1,[]));
    records(k)=struct('path',relative,'sha256',checksum,'bytes',numel(bytes));
    clear cleanup;
end
end
