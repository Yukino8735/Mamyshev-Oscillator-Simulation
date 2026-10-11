function report=test_launchprep_capture(output_dir)
% Small comparison protocol fixtures; never initializes or propagates a cavity.
root=fileparts(fileparts(fileparts(mfilename('fullpath'))));
addpath(fullfile(root,'code','ml_bridge'));
fixture_dir=fullfile(output_dir,'capture_component'); mkdir(fixture_dir);
phase1_config=struct('Nt',4,'sim_cavity',struct('cuda_dir_path','old/path','deltaZ',0.001), ...
    'rng',struct('Type','twister','Seed',0,'State',uint32([1;2])));
gain_param={struct('t_rep',1),struct('absorption',[1;2]),complex([1;2],[0;1])};
prop_output=struct('dt',0.1,'fields',complex((1:4)',(4:-1:1)'));
t=0:3; f=(1:4)'; lambda=5:8;
reference=fullfile(fixture_dir,'synthetic_reference.mat');
save(reference,'phase1_config','gain_param','prop_output','t','f','lambda');
value=struct('phase1_config',phase1_config,'gain_param',{gain_param}, ...
    'prop_output',prop_output,'t',t,'f',f,'lambda',lambda);
cases=struct('name',{},'passed',{});
check('exact_recursive_values_and_shapes',mamyshev_compare_configuration(value,reference).passed);
altered=value; altered.prop_output.fields(1)=altered.prop_output.fields(1)+eps;
check('complex_field_value_change_rejected',~mamyshev_compare_configuration(altered,reference).passed);
altered=value; altered.t=altered.t';
check('grid_shape_change_rejected',~mamyshev_compare_configuration(altered,reference).passed);
altered=value; altered.gain_param{2}.absorption=single([1;2]);
check('gain_array_class_change_rejected',~mamyshev_compare_configuration(altered,reference).passed);
altered=rmfield(value,'f');
check('critical_grid_missing_rejected',~mamyshev_compare_configuration(altered,reference).passed);
altered=value; altered.phase1_config.sim_cavity.cuda_dir_path='new/path';
comparison=mamyshev_compare_configuration(altered,reference);
check('installation_path_only_expected_metadata',comparison.passed && numel(comparison.expected_metadata_differences)==1);
altered=value; altered.phase1_config.sim_cavity.deltaZ=0.002;
check('step_value_change_rejected',~mamyshev_compare_configuration(altered,reference).passed);
altered=value; altered.phase1_config.sim_cavity.test_hook=[];
check('new_numerical_field_rejected',~mamyshev_compare_configuration(altered,reference).passed);
before=rng;
mamyshev_write_diagnostic(fullfile(fixture_dir,'rng_writer.json'),struct('value',1));
check('diagnostic_writer_preserves_rng',isequal(before,rng));
existing_rejected=false;
try, mamyshev_write_diagnostic(fullfile(fixture_dir,'rng_writer.json'),struct('value',2));
catch exception, existing_rejected=strcmp(exception.identifier,'MamyshevRecord:ExistingRecord'); end
check('diagnostic_writer_refuses_existing_evidence',existing_rejected);
context=struct('mode','real'); injection=struct('kind','wrapper_component_fixture','backend',@forbidden_backend);
injection_rejected=false;
try, run_mamyshev_recorded(4,1030,false,fullfile(fixture_dir,'matlab_candidate.json'),injection,context);
catch exception, injection_rejected=strcmp(exception.identifier,'MamyshevRecord:RealBackendInjection'); end
check('real_mode_rejects_injected_backend_before_call',injection_rejected);
% Reuse directly captured legacy bytes only to exercise the comparison helper.
% This read does not initialize a physical configuration or call propagation.
baseline=fullfile(root,'reports','local','phase1','baseline_001','configuration.mat');
historical=load(baseline,'phase1_config','gain_param','prop_output','t','f','lambda');
comparison=mamyshev_compare_configuration(historical,baseline);
check('direct_baseline_mat_schema_supported',comparison.passed);
% Artifact identity uses actual MAT/JSON bytes, distinct from parameter content
% validation. Corrupt only a newly copied synthetic fixture, never old evidence.
before=rng;
integrity=mamyshev_artifact_integrity(fixture_dir,{'synthetic_reference.mat','rng_writer.json'});
sizes=[dir(reference);dir(fullfile(fixture_dir,'rng_writer.json'))];
check('artifact_hashes_actual_mat_json_bytes_and_preserves_rng', ...
    isequal(before,rng) && all([integrity.bytes]==[sizes.bytes]) && ...
    all(arrayfun(@(x)numel(x.sha256)==64,integrity)));
mutated=fullfile(fixture_dir,'integrity_mutated.mat'); copyfile(reference,mutated);
fid=fopen(mutated,'ab'); assert(fid>=0); fwrite(fid,uint8(0),'uint8'); fclose(fid);
changed=mamyshev_artifact_integrity(fixture_dir,{'integrity_mutated.mat'});
check('artifact_byte_mutation_changes_identity', ...
    ~strcmp(changed.sha256,integrity(1).sha256) && changed.bytes==integrity(1).bytes+1);
report=struct('suite','capture_component','full_cavity_attempts',0,'initialization_attempts',0, ...
    'fixture_only',true,'cases',cases,'all_passed',all([cases.passed]), ...
    'comparison_rule','Exact values/classes/shapes; only named metadata excluded');
mamyshev_write_diagnostic(fullfile(output_dir,'capture_component.json'),report);
    function check(name,passed)
        cases(end+1)=struct('name',name,'passed',passed);
        assert(passed,'Launchprep:CaptureAssertion','%s',name);
    end
end
function value=forbidden_backend(varargin)
error('Launchprep:ForbiddenBackendCalled','Real mode must reject before fixture invocation.');
value=[]; %#ok<UNRCH>
end
