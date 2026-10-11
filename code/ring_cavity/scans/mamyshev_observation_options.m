function options=mamyshev_observation_options(options,max_rt)
% Separate observation protocol; never a fifth physical design input.
if nargin<2, max_rt=50; end
if nargin<1
    options=struct('observation_mode','legacy','observation_roundtrips',[]);
end
assert(isstruct(options) && isscalar(options) && ...
    isequal(sort(fieldnames(options)),sort({'observation_mode';'observation_roundtrips'})), ...
    'MamyshevObservation:Fields','Exactly observation_mode and observation_roundtrips are required.');
assert(ischar(options.observation_mode) && isrow(options.observation_mode), ...
    'MamyshevObservation:Mode','Mode must be legacy or fixed_roundtrips.');
switch options.observation_mode
    case 'legacy'
        assert(isempty(options.observation_roundtrips),'MamyshevObservation:Conflict', ...
            'Legacy mode does not accept a fixed observation count.');
    case 'fixed_roundtrips'
        n=options.observation_roundtrips;
        assert(isnumeric(n) && ~islogical(n) && isscalar(n) && isreal(n) && ...
            isfinite(n) && n==fix(n) && n>=1 && n<=max_rt, ...
            'MamyshevObservation:RoundCount','Observation count must be an integer from one through unchanged max_rt.');
        options.observation_roundtrips=double(n);
    otherwise
        error('MamyshevObservation:Mode','Unknown observation mode.');
end
end
