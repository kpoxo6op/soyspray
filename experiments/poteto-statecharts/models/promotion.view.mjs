export const title = 'Source delivery and separate digest promotion';
export const state = v => v.running === 'New' ? (v.approved ? 'New image running after promotion' : 'New image running without promotion') : v.approved ? 'Promotion merged; old image running' : v.artifact === 'Published' ? 'Image published; old image running' : v.artifact === 'Tested' ? 'Image tested; old image running' : v.source === 'New' ? 'Source merged; old image running' : 'Original source and running image';
export const step = a => ({MergeSource:'merge source change',BuildAndTest:'build and test image',PublishImage:'publish digest',MergePromotion:'merge separate promotion',Reconcile:'Argo reconciles main',Done:null}[a] ?? a);
export const group = v => v.running === 'New' ? 'ready' : 'pending';
export const colors = {ready:'teal',pending:'blue'};
