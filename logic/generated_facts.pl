% Generated from validated ArtGraph v1.0 RDF. Do not edit.
:- dynamic source_fact/5.
:- dynamic fact_snapshot/2.
:- dynamic rdf_type/3.
:- dynamic rdf_label/3.
:- dynamic created_by/3.
:- dynamic has_style/3.
:- dynamic has_genre/3.
:- dynamic made_of/3.
:- dynamic belongs_to_movement/3.
:- discontiguous source_fact/5.
:- discontiguous fact_snapshot/2.
:- discontiguous rdf_type/3.
:- discontiguous rdf_label/3.
:- discontiguous created_by/3.
:- discontiguous has_style/3.
:- discontiguous has_genre/3.
:- discontiguous made_of/3.
:- discontiguous belongs_to_movement/3.
snapshot(artgraph_v1_seed_8142).
source_dataset(artgraph_v1_seed_8142, 'https://zenodo.org/records/6337958').
topic(ag_12, genre, 'religious painting', 'https://www.gennarovessio.com/artgraph-resources#12').
topic(ag_2551, medium, oil, 'https://www.gennarovessio.com/artgraph-resources#2551').
topic(ag_2552, medium, canvas, 'https://www.gennarovessio.com/artgraph-resources#2552').
topic(ag_46, style, 'mannerism (late renaissance)', 'https://www.gennarovessio.com/artgraph-resources#46').
topic(ag_8142, artwork, 'Portrait of Eve', 'https://www.gennarovessio.com/artgraph-resources#8142').
topic(ag_8143, artwork, 'Portrait of Adam', 'https://www.gennarovessio.com/artgraph-resources#8143').
topic(ag_8144, artwork, 'The Vegetable Gardener', 'https://www.gennarovessio.com/artgraph-resources#8144').
topic(ag_850, artist, 'giuseppe-arcimboldo', 'https://www.gennarovessio.com/artgraph-resources#850').
rdf_type(ag_12, genre, agf_8104aa86f3be61082cf8).
source_fact(agf_8104aa86f3be61082cf8, rdf_type, ag_12, genre, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_8104aa86f3be61082cf8, artgraph_v1_seed_8142).
rdf_label(ag_12, 'religious painting', agf_2128353d33ea9174f2bf).
source_fact(agf_2128353d33ea9174f2bf, rdf_label, ag_12, 'religious painting', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_2128353d33ea9174f2bf, artgraph_v1_seed_8142).
rdf_type(ag_2551, medium, agf_4a8f83e3a05c54f220e3).
source_fact(agf_4a8f83e3a05c54f220e3, rdf_type, ag_2551, medium, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_4a8f83e3a05c54f220e3, artgraph_v1_seed_8142).
rdf_label(ag_2551, oil, agf_c867b269544371d05714).
source_fact(agf_c867b269544371d05714, rdf_label, ag_2551, oil, 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_c867b269544371d05714, artgraph_v1_seed_8142).
rdf_type(ag_2552, medium, agf_2b81e5732ea9cfd457c6).
source_fact(agf_2b81e5732ea9cfd457c6, rdf_type, ag_2552, medium, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_2b81e5732ea9cfd457c6, artgraph_v1_seed_8142).
rdf_label(ag_2552, canvas, agf_4d4403d9766906cf8396).
source_fact(agf_4d4403d9766906cf8396, rdf_label, ag_2552, canvas, 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_4d4403d9766906cf8396, artgraph_v1_seed_8142).
rdf_type(ag_46, style, agf_fed09cc2b3e97fc5baea).
source_fact(agf_fed09cc2b3e97fc5baea, rdf_type, ag_46, style, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_fed09cc2b3e97fc5baea, artgraph_v1_seed_8142).
rdf_label(ag_46, 'mannerism (late renaissance)', agf_05e15a2e078516553fa7).
source_fact(agf_05e15a2e078516553fa7, rdf_label, ag_46, 'mannerism (late renaissance)', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_05e15a2e078516553fa7, artgraph_v1_seed_8142).
rdf_type(ag_8142, artwork, agf_836bfb0036fa769cbb29).
source_fact(agf_836bfb0036fa769cbb29, rdf_type, ag_8142, artwork, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_836bfb0036fa769cbb29, artgraph_v1_seed_8142).
created_by(ag_8142, ag_850, agf_0afc2259bcbb7540bc3a).
source_fact(agf_0afc2259bcbb7540bc3a, created_by, ag_8142, ag_850, 'https://www.gennarovessio.com/artgraph-schema#createdBy').
fact_snapshot(agf_0afc2259bcbb7540bc3a, artgraph_v1_seed_8142).
has_genre(ag_8142, ag_12, agf_96da2e7e58c5299da472).
source_fact(agf_96da2e7e58c5299da472, has_genre, ag_8142, ag_12, 'https://www.gennarovessio.com/artgraph-schema#hasGenre').
fact_snapshot(agf_96da2e7e58c5299da472, artgraph_v1_seed_8142).
has_style(ag_8142, ag_46, agf_e6d7228f5b9de1451761).
source_fact(agf_e6d7228f5b9de1451761, has_style, ag_8142, ag_46, 'https://www.gennarovessio.com/artgraph-schema#hasStyle').
fact_snapshot(agf_e6d7228f5b9de1451761, artgraph_v1_seed_8142).
made_of(ag_8142, ag_2551, agf_5158a37d998121d1de34).
source_fact(agf_5158a37d998121d1de34, made_of, ag_8142, ag_2551, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_5158a37d998121d1de34, artgraph_v1_seed_8142).
made_of(ag_8142, ag_2552, agf_205d36c4ffd9fd22c396).
source_fact(agf_205d36c4ffd9fd22c396, made_of, ag_8142, ag_2552, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_205d36c4ffd9fd22c396, artgraph_v1_seed_8142).
rdf_label(ag_8142, 'giuseppe-arcimboldo_portrait-of-eve-1578.jpg', agf_331448c8d8c1678f9a7d).
source_fact(agf_331448c8d8c1678f9a7d, rdf_label, ag_8142, 'giuseppe-arcimboldo_portrait-of-eve-1578.jpg', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_331448c8d8c1678f9a7d, artgraph_v1_seed_8142).
rdf_label(ag_8142, 'Portrait of Eve', agf_032f4c899e074ac7c253).
source_fact(agf_032f4c899e074ac7c253, rdf_label, ag_8142, 'Portrait of Eve', 'https://www.gennarovessio.com/artgraph-schema#title').
fact_snapshot(agf_032f4c899e074ac7c253, artgraph_v1_seed_8142).
rdf_type(ag_8143, artwork, agf_21a98cd187b88ae70186).
source_fact(agf_21a98cd187b88ae70186, rdf_type, ag_8143, artwork, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_21a98cd187b88ae70186, artgraph_v1_seed_8142).
created_by(ag_8143, ag_850, agf_a39c8525c0746b5230e4).
source_fact(agf_a39c8525c0746b5230e4, created_by, ag_8143, ag_850, 'https://www.gennarovessio.com/artgraph-schema#createdBy').
fact_snapshot(agf_a39c8525c0746b5230e4, artgraph_v1_seed_8142).
has_genre(ag_8143, ag_12, agf_c0c359e13fdc90a0588c).
source_fact(agf_c0c359e13fdc90a0588c, has_genre, ag_8143, ag_12, 'https://www.gennarovessio.com/artgraph-schema#hasGenre').
fact_snapshot(agf_c0c359e13fdc90a0588c, artgraph_v1_seed_8142).
has_style(ag_8143, ag_46, agf_eb98107be4c0253ce2a2).
source_fact(agf_eb98107be4c0253ce2a2, has_style, ag_8143, ag_46, 'https://www.gennarovessio.com/artgraph-schema#hasStyle').
fact_snapshot(agf_eb98107be4c0253ce2a2, artgraph_v1_seed_8142).
made_of(ag_8143, ag_2551, agf_2c3916b5a8b10dcbd9b5).
source_fact(agf_2c3916b5a8b10dcbd9b5, made_of, ag_8143, ag_2551, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_2c3916b5a8b10dcbd9b5, artgraph_v1_seed_8142).
made_of(ag_8143, ag_2552, agf_f485f7cb8d94c943c749).
source_fact(agf_f485f7cb8d94c943c749, made_of, ag_8143, ag_2552, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_f485f7cb8d94c943c749, artgraph_v1_seed_8142).
rdf_label(ag_8143, 'giuseppe-arcimboldo_portrait-of-adam-1578.jpg', agf_0dd7c1bb3c56e36fb2e1).
source_fact(agf_0dd7c1bb3c56e36fb2e1, rdf_label, ag_8143, 'giuseppe-arcimboldo_portrait-of-adam-1578.jpg', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_0dd7c1bb3c56e36fb2e1, artgraph_v1_seed_8142).
rdf_label(ag_8143, 'Portrait of Adam', agf_efa8c6d941bc252cf18b).
source_fact(agf_efa8c6d941bc252cf18b, rdf_label, ag_8143, 'Portrait of Adam', 'https://www.gennarovessio.com/artgraph-schema#title').
fact_snapshot(agf_efa8c6d941bc252cf18b, artgraph_v1_seed_8142).
rdf_type(ag_8144, artwork, agf_df0d42679eab3be72773).
source_fact(agf_df0d42679eab3be72773, rdf_type, ag_8144, artwork, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_df0d42679eab3be72773, artgraph_v1_seed_8142).
created_by(ag_8144, ag_850, agf_c92266757f11b249d1b0).
source_fact(agf_c92266757f11b249d1b0, created_by, ag_8144, ag_850, 'https://www.gennarovessio.com/artgraph-schema#createdBy').
fact_snapshot(agf_c92266757f11b249d1b0, artgraph_v1_seed_8142).
has_style(ag_8144, ag_46, agf_4aae4c0380d40b95f38a).
source_fact(agf_4aae4c0380d40b95f38a, has_style, ag_8144, ag_46, 'https://www.gennarovessio.com/artgraph-schema#hasStyle').
fact_snapshot(agf_4aae4c0380d40b95f38a, artgraph_v1_seed_8142).
made_of(ag_8144, ag_2551, agf_14d728eaed44b42fe4b3).
source_fact(agf_14d728eaed44b42fe4b3, made_of, ag_8144, ag_2551, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_14d728eaed44b42fe4b3, artgraph_v1_seed_8142).
rdf_label(ag_8144, 'giuseppe-arcimboldo_the-vegetable-bowl.jpg', agf_7249a0dbc8d02dd7b831).
source_fact(agf_7249a0dbc8d02dd7b831, rdf_label, ag_8144, 'giuseppe-arcimboldo_the-vegetable-bowl.jpg', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_7249a0dbc8d02dd7b831, artgraph_v1_seed_8142).
rdf_label(ag_8144, 'The Vegetable Gardener', agf_2bb8a651413ee5d125e0).
source_fact(agf_2bb8a651413ee5d125e0, rdf_label, ag_8144, 'The Vegetable Gardener', 'https://www.gennarovessio.com/artgraph-schema#title').
fact_snapshot(agf_2bb8a651413ee5d125e0, artgraph_v1_seed_8142).
rdf_type(ag_850, artist, agf_e5c20609889b7e76389d).
source_fact(agf_e5c20609889b7e76389d, rdf_type, ag_850, artist, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_e5c20609889b7e76389d, artgraph_v1_seed_8142).
rdf_label(ag_850, 'giuseppe-arcimboldo', agf_f2358835f0d6fbd9e2a2).
source_fact(agf_f2358835f0d6fbd9e2a2, rdf_label, ag_850, 'giuseppe-arcimboldo', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_f2358835f0d6fbd9e2a2, artgraph_v1_seed_8142).
