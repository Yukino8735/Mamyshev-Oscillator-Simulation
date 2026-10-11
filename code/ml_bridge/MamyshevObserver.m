classdef MamyshevObserver < handle
    %MAMYSHEVOBSERVER Read-only scalar diagnostics, independent of test_hook.
    % No numerical state or physical random numbers are read or modified.
    % An active on-disk segment has null counters: a killed process cannot
    % leave its unflushed in-memory progress looking like complete evidence.
    properties (SetAccess=private)
        version = 'launchprep_001_readonly_observer_v1'
        identity
        record_path
        segments = {}
        active = []
    end
    methods
        function obj = MamyshevObserver(record_path,identity)
            if nargin<1, record_path=''; end
            if nargin<2, identity=struct(); end
            obj.record_path=record_path; obj.identity=identity;
            if ~isempty(record_path)
                assert(~isfile(record_path) && ~isfile([record_path '.tmp']), ...
                    'MamyshevObserver:ExistingEvidence','Refusing to overwrite observer evidence.');
            end
        end
        function begin_segment(obj,rt,segment_id,kind,call_metadata)
            if nargin<5, call_metadata=struct(); end
            assert(isempty(obj.active),'MamyshevObserver:ActiveSegment');
            obj.active=struct('round_trip',rt,'segment_id',segment_id,'kind',kind, ...
                'capture_time_utc',obj.utc_now(),'capture_location','actual propagation call boundary', ...
                'parameter_source','arguments passed to production GMMNLSE_propagate', ...
                'call_metadata',call_metadata,'runtime_resolutions',{{}}, ...
                'trials',0,'rejections',0,'accepted_advanced_steps',0,'pending_trials',0, ...
                'last_advanced_z_m',0,'normal_completion',false,'counts_complete',false, ...
                'count_source','production trial / reject decision / z advancement', ...
                'incomplete_reason','active_segment_counters_not_flushed');
            obj.flush();
        end
        function resolved(obj,sim,source,extra)
            if nargin<4, extra=struct(); end
            obj.require_active();
            item=struct('status','observed','capture_time_utc',obj.utc_now(), ...
                'capture_location',source,'parameter_source','actual local sim after step initialization', ...
                'max_deltaZ',sim.adaptive_deltaZ.max_deltaZ,'initial_deltaZ',sim.deltaZ, ...
                'threshold',sim.adaptive_deltaZ.threshold,'save_period',sim.save_period, ...
                'units',struct('max_deltaZ','m','initial_deltaZ','m', ...
                    'threshold','dimensionless relative error','save_period','m'), ...
                'extra',extra);
            obj.active.runtime_resolutions{end+1}=item;
            obj.flush();
        end
        function trial(obj)
            obj.require_active();
            obj.active.trials=obj.active.trials+1;
            obj.active.pending_trials=obj.active.pending_trials+1;
        end
        function reject(obj)
            obj.require_active();
            obj.active.rejections=obj.active.rejections+1;
            obj.active.pending_trials=obj.active.pending_trials-1;
        end
        function advanced(obj,z)
            obj.require_active();
            obj.active.accepted_advanced_steps=obj.active.accepted_advanced_steps+1;
            obj.active.pending_trials=obj.active.pending_trials-1;
            obj.active.last_advanced_z_m=z;
        end
        function complete_segment(obj)
            obj.require_active();
            assert(obj.active.pending_trials==0 && ...
                obj.active.trials==obj.active.rejections+obj.active.accepted_advanced_steps, ...
                'MamyshevObserver:IncompleteCounts','Production decision/advance counts do not balance.');
            assert(~isempty(obj.active.runtime_resolutions), ...
                'MamyshevObserver:MissingResolution','No runtime step resolution was observed.');
            obj.active.normal_completion=true; obj.active.counts_complete=true;
            obj.active.incomplete_reason=''; obj.active.end_time_utc=obj.utc_now();
            obj.segments{end+1}=obj.active; obj.active=[];
            obj.flush();
        end
        function abort_segment(obj,reason)
            if isempty(obj.active), return; end
            obj.active.incomplete_reason=reason;
            item=obj.active; item.counts_complete=false; item.normal_completion=false;
            item.count_source='partial in-memory counters observed at exception handler; not normal completion';
            item.end_time_utc=obj.utc_now();
            obj.segments{end+1}=item; obj.active=[];
            obj.flush();
        end
        function result=summary(obj)
            result=struct('observer_version',obj.version,'identity',obj.identity, ...
                'segments',{obj.segments},'active_segment',[], ...
                'counts_complete',isempty(obj.active) && ~isempty(obj.segments) && ...
                    all(cellfun(@(x)x.counts_complete,obj.segments)), ...
                'segment_count',numel(obj.segments), ...
                'runtime_resolved_complete',isempty(obj.active) && ~isempty(obj.segments) && ...
                    all(cellfun(@(x)~isempty(x.runtime_resolutions) && x.counts_complete,obj.segments)), ...
                'status','observed','units',struct('z','m','counts','integer events'));
            if ~isempty(obj.active)
                result.active_segment=obj.active;
                names={'trials','rejections','accepted_advanced_steps','pending_trials','last_advanced_z_m'};
                for k=1:numel(names), result.active_segment.(names{k})=NaN; end
                result.active_segment.count_source='unflushed active segment; values unavailable';
            end
        end
    end
    methods (Access=private)
        function require_active(obj)
            assert(~isempty(obj.active),'MamyshevObserver:NoActiveSegment');
        end
        function flush(obj)
            if isempty(obj.record_path), return; end
            % Fixed sibling temp is private to this single writer/run. Unlike
            % rand/randi-based names, it cannot perturb the physical RNG.
            temporary=[obj.record_path '.tmp'];
            fid=fopen(temporary,'wb');
            assert(fid>=0,'MamyshevObserver:WriteError','Cannot open observer temporary.');
            try
                payload=jsonencode(obj.summary(),'ConvertInfAndNaN',true,'PrettyPrint',true);
                bytes=unicode2native([payload newline],'UTF-8');
                count=fwrite(fid,bytes,'uint8'); closed=fclose(fid); fid=-1;
                assert(count==numel(bytes) && closed==0, ...
                    'MamyshevObserver:WriteError','Observer write/close failed.');
                [ok,message]=movefile(temporary,obj.record_path,'f');
                assert(ok,'MamyshevObserver:WriteError','Observer publish failed: %s',message);
            catch exception
                if fid>=0, fclose(fid); end
                rethrow(exception);
            end
        end
    end
    methods (Static,Access=private)
        function value=utc_now()
            value=char(datetime('now','TimeZone','UTC','Format',"yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"));
        end
    end
end
