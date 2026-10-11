function result=run_mamyshev_config(config,plot_on,diagnostic_options)
% Configuration entry sharing the original initialization and production loop.
% No fields beyond the four named design inputs are accepted. Omit the whole
% configuration to request the documented default; partial structs are errors.
if nargin<1, config=mamyshev_resolve_config(); end
if nargin<2, plot_on=false; end
if nargin<3, diagnostic_options=[]; end
config=mamyshev_resolve_config(config);
result=run_mamyshev([],[],plot_on,diagnostic_options,config);
end
