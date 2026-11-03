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
:- dynamic has_subject/3.
:- dynamic has_period/3.
:- dynamic part_of_series/3.
:- dynamic related_to_school/3.
:- discontiguous source_fact/5.
:- discontiguous fact_snapshot/2.
:- discontiguous rdf_type/3.
:- discontiguous rdf_label/3.
:- discontiguous created_by/3.
:- discontiguous has_style/3.
:- discontiguous has_genre/3.
:- discontiguous made_of/3.
:- discontiguous belongs_to_movement/3.
:- discontiguous has_subject/3.
:- discontiguous has_period/3.
:- discontiguous part_of_series/3.
:- discontiguous related_to_school/3.
snapshot(artgraph_v1_phase_0_5_morris_louis).
source_dataset(artgraph_v1_phase_0_5_morris_louis, 'https://zenodo.org/records/6337958').
topic(ag_1210, artist, 'morris-louis', 'https://www.gennarovessio.com/artgraph-resources#1210').
topic(ag_124645, movement, 'Washington Color School', 'https://www.gennarovessio.com/artgraph-resources#124645').
topic(ag_124741, movement, 'Color field', 'https://www.gennarovessio.com/artgraph-resources#124741').
topic(ag_124790, movement, 'Post-painterly abstraction', 'https://www.gennarovessio.com/artgraph-resources#124790').
topic(ag_124822, training, 'Maryland Institute College of Art', 'https://www.gennarovessio.com/artgraph-resources#124822').
topic(ag_125194, subject, 'Jewish American artists', 'https://www.gennarovessio.com/artgraph-resources#125194').
topic(ag_126039, subject, 'Artists from Washington, D.C.', 'https://www.gennarovessio.com/artgraph-resources#126039').
topic(ag_126052, subject, 'Abstract expressionist artists', 'https://www.gennarovessio.com/artgraph-resources#126052').
topic(ag_132587, series, 'Stripe', 'https://www.gennarovessio.com/artgraph-resources#132587').
topic(ag_132804, series, 'Veil', 'https://www.gennarovessio.com/artgraph-resources#132804').
topic(ag_132972, series, 'Unfurled', 'https://www.gennarovessio.com/artgraph-resources#132972').
topic(ag_133221, period, 'Mature Works', 'https://www.gennarovessio.com/artgraph-resources#133221').
topic(ag_2552, medium, canvas, 'https://www.gennarovessio.com/artgraph-resources#2552').
topic(ag_2602, medium, magna, 'https://www.gennarovessio.com/artgraph-resources#2602').
topic(ag_2630, medium, acrylic, 'https://www.gennarovessio.com/artgraph-resources#2630').
topic(ag_41, style, 'color field painting', 'https://www.gennarovessio.com/artgraph-resources#41').
topic(ag_6, genre, abstract, 'https://www.gennarovessio.com/artgraph-resources#6').
topic(ag_72463, artwork, 'Where', 'https://www.gennarovessio.com/artgraph-resources#72463').
topic(ag_72464, artwork, 'Alpha-Pi', 'https://www.gennarovessio.com/artgraph-resources#72464').
topic(ag_72465, artwork, 'Beta Lambda', 'https://www.gennarovessio.com/artgraph-resources#72465').
topic(ag_72466, artwork, 'Partition', 'https://www.gennarovessio.com/artgraph-resources#72466').
topic(ag_72467, artwork, 'Phi', 'https://www.gennarovessio.com/artgraph-resources#72467').
topic(ag_72468, artwork, 'VAV', 'https://www.gennarovessio.com/artgraph-resources#72468').
rdf_type(ag_1210, artist, agf_80e115b95501926d3a23).
source_fact(agf_80e115b95501926d3a23, rdf_type, ag_1210, artist, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_80e115b95501926d3a23, artgraph_v1_phase_0_5_morris_louis).
belongs_to_movement(ag_1210, ag_124645, agf_5105e623d3f9451b253c).
source_fact(agf_5105e623d3f9451b253c, belongs_to_movement, ag_1210, ag_124645, 'https://www.gennarovessio.com/artgraph-schema#belongsToMovement').
fact_snapshot(agf_5105e623d3f9451b253c, artgraph_v1_phase_0_5_morris_louis).
belongs_to_movement(ag_1210, ag_124741, agf_bb3f3b203fb979c32ae9).
source_fact(agf_bb3f3b203fb979c32ae9, belongs_to_movement, ag_1210, ag_124741, 'https://www.gennarovessio.com/artgraph-schema#belongsToMovement').
fact_snapshot(agf_bb3f3b203fb979c32ae9, artgraph_v1_phase_0_5_morris_louis).
belongs_to_movement(ag_1210, ag_124790, agf_31542e0f5ce7872fb007).
source_fact(agf_31542e0f5ce7872fb007, belongs_to_movement, ag_1210, ag_124790, 'https://www.gennarovessio.com/artgraph-schema#belongsToMovement').
fact_snapshot(agf_31542e0f5ce7872fb007, artgraph_v1_phase_0_5_morris_louis).
has_subject(ag_1210, ag_125194, agf_ededfdfc744d27829256).
source_fact(agf_ededfdfc744d27829256, has_subject, ag_1210, ag_125194, 'https://www.gennarovessio.com/artgraph-schema#hasSubject').
fact_snapshot(agf_ededfdfc744d27829256, artgraph_v1_phase_0_5_morris_louis).
has_subject(ag_1210, ag_126039, agf_f061340a618d6cc2515e).
source_fact(agf_f061340a618d6cc2515e, has_subject, ag_1210, ag_126039, 'https://www.gennarovessio.com/artgraph-schema#hasSubject').
fact_snapshot(agf_f061340a618d6cc2515e, artgraph_v1_phase_0_5_morris_louis).
has_subject(ag_1210, ag_126052, agf_725f28cb403e1feea7cb).
source_fact(agf_725f28cb403e1feea7cb, has_subject, ag_1210, ag_126052, 'https://www.gennarovessio.com/artgraph-schema#hasSubject').
fact_snapshot(agf_725f28cb403e1feea7cb, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_1210, 'morris-louis', agf_8056a6eb6227c61f0a70).
source_fact(agf_8056a6eb6227c61f0a70, rdf_label, ag_1210, 'morris-louis', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_8056a6eb6227c61f0a70, artgraph_v1_phase_0_5_morris_louis).
related_to_school(ag_1210, ag_124822, agf_cf509646c43cace3bef5).
source_fact(agf_cf509646c43cace3bef5, related_to_school, ag_1210, ag_124822, 'https://www.gennarovessio.com/artgraph-schema#relatedToSchool').
fact_snapshot(agf_cf509646c43cace3bef5, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_124645, movement, agf_1f4b36badbf19c57956b).
source_fact(agf_1f4b36badbf19c57956b, rdf_type, ag_124645, movement, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_1f4b36badbf19c57956b, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_124645, 'Washington Color School', agf_de437c31e020007630c0).
source_fact(agf_de437c31e020007630c0, rdf_label, ag_124645, 'Washington Color School', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_de437c31e020007630c0, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_124741, movement, agf_921f4ea2f0d316f7f9ee).
source_fact(agf_921f4ea2f0d316f7f9ee, rdf_type, ag_124741, movement, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_921f4ea2f0d316f7f9ee, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_124741, 'Color field', agf_66f067f829b32dde737c).
source_fact(agf_66f067f829b32dde737c, rdf_label, ag_124741, 'Color field', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_66f067f829b32dde737c, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_124790, movement, agf_e58e9a79cb0386772611).
source_fact(agf_e58e9a79cb0386772611, rdf_type, ag_124790, movement, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_e58e9a79cb0386772611, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_124790, 'Post-painterly abstraction', agf_4ceece6299083d7d71e6).
source_fact(agf_4ceece6299083d7d71e6, rdf_label, ag_124790, 'Post-painterly abstraction', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_4ceece6299083d7d71e6, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_124822, training, agf_111ba8c904546200e42a).
source_fact(agf_111ba8c904546200e42a, rdf_type, ag_124822, training, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_111ba8c904546200e42a, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_124822, 'Maryland Institute College of Art', agf_344a542943c2a9f09189).
source_fact(agf_344a542943c2a9f09189, rdf_label, ag_124822, 'Maryland Institute College of Art', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_344a542943c2a9f09189, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_125194, subject, agf_75696a134433f27561cd).
source_fact(agf_75696a134433f27561cd, rdf_type, ag_125194, subject, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_75696a134433f27561cd, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_125194, 'Jewish American artists', agf_b51d9faadb2c4a895881).
source_fact(agf_b51d9faadb2c4a895881, rdf_label, ag_125194, 'Jewish American artists', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_b51d9faadb2c4a895881, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_126039, subject, agf_4c5506b4b6de568dee7e).
source_fact(agf_4c5506b4b6de568dee7e, rdf_type, ag_126039, subject, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_4c5506b4b6de568dee7e, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_126039, 'Artists from Washington, D.C.', agf_f30aa539f82b8341cc55).
source_fact(agf_f30aa539f82b8341cc55, rdf_label, ag_126039, 'Artists from Washington, D.C.', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_f30aa539f82b8341cc55, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_126052, subject, agf_ce1f27dfffdf6f680be0).
source_fact(agf_ce1f27dfffdf6f680be0, rdf_type, ag_126052, subject, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_ce1f27dfffdf6f680be0, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_126052, 'Abstract expressionist artists', agf_ce75e174d563467817cc).
source_fact(agf_ce75e174d563467817cc, rdf_label, ag_126052, 'Abstract expressionist artists', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_ce75e174d563467817cc, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_132587, series, agf_fc31b58b9f47b9b0ec30).
source_fact(agf_fc31b58b9f47b9b0ec30, rdf_type, ag_132587, series, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_fc31b58b9f47b9b0ec30, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_132587, 'Stripe', agf_984afc42430e2a03b1a1).
source_fact(agf_984afc42430e2a03b1a1, rdf_label, ag_132587, 'Stripe', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_984afc42430e2a03b1a1, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_132804, series, agf_ee682cf72eb07ea7ca52).
source_fact(agf_ee682cf72eb07ea7ca52, rdf_type, ag_132804, series, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_ee682cf72eb07ea7ca52, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_132804, 'Veil', agf_4c9f6125fef211026dcf).
source_fact(agf_4c9f6125fef211026dcf, rdf_label, ag_132804, 'Veil', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_4c9f6125fef211026dcf, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_132972, series, agf_ab2c7f647a666e45cbb3).
source_fact(agf_ab2c7f647a666e45cbb3, rdf_type, ag_132972, series, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_ab2c7f647a666e45cbb3, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_132972, 'Unfurled', agf_912e33f3c4ac4112d3f0).
source_fact(agf_912e33f3c4ac4112d3f0, rdf_label, ag_132972, 'Unfurled', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_912e33f3c4ac4112d3f0, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_133221, period, agf_7063fa2305e091ebf8d4).
source_fact(agf_7063fa2305e091ebf8d4, rdf_type, ag_133221, period, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_7063fa2305e091ebf8d4, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_133221, 'Mature Works', agf_e3ecd3ff5db925cfdcc6).
source_fact(agf_e3ecd3ff5db925cfdcc6, rdf_label, ag_133221, 'Mature Works', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_e3ecd3ff5db925cfdcc6, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_2552, medium, agf_2b81e5732ea9cfd457c6).
source_fact(agf_2b81e5732ea9cfd457c6, rdf_type, ag_2552, medium, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_2b81e5732ea9cfd457c6, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_2552, canvas, agf_4d4403d9766906cf8396).
source_fact(agf_4d4403d9766906cf8396, rdf_label, ag_2552, canvas, 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_4d4403d9766906cf8396, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_2602, medium, agf_cbf3caf7a70f426dee18).
source_fact(agf_cbf3caf7a70f426dee18, rdf_type, ag_2602, medium, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_cbf3caf7a70f426dee18, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_2602, magna, agf_569498c6dae989b367de).
source_fact(agf_569498c6dae989b367de, rdf_label, ag_2602, magna, 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_569498c6dae989b367de, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_2630, medium, agf_dc4ad5c6a6e80a28b274).
source_fact(agf_dc4ad5c6a6e80a28b274, rdf_type, ag_2630, medium, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_dc4ad5c6a6e80a28b274, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_2630, acrylic, agf_604f6fd317dc699c9e92).
source_fact(agf_604f6fd317dc699c9e92, rdf_label, ag_2630, acrylic, 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_604f6fd317dc699c9e92, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_41, style, agf_271ef9bab85d8be3eba4).
source_fact(agf_271ef9bab85d8be3eba4, rdf_type, ag_41, style, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_271ef9bab85d8be3eba4, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_41, 'color field painting', agf_481987b8522885ddb8bb).
source_fact(agf_481987b8522885ddb8bb, rdf_label, ag_41, 'color field painting', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_481987b8522885ddb8bb, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_6, genre, agf_e66d5d4b6517d53898ca).
source_fact(agf_e66d5d4b6517d53898ca, rdf_type, ag_6, genre, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_e66d5d4b6517d53898ca, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_6, abstract, agf_d3bc188d25fea49ce594).
source_fact(agf_d3bc188d25fea49ce594, rdf_label, ag_6, abstract, 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_d3bc188d25fea49ce594, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_72463, artwork, agf_9dca06eb4131f9164d9b).
source_fact(agf_9dca06eb4131f9164d9b, rdf_type, ag_72463, artwork, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_9dca06eb4131f9164d9b, artgraph_v1_phase_0_5_morris_louis).
created_by(ag_72463, ag_1210, agf_ac9cf6f7052a601f3faa).
source_fact(agf_ac9cf6f7052a601f3faa, created_by, ag_72463, ag_1210, 'https://www.gennarovessio.com/artgraph-schema#createdBy').
fact_snapshot(agf_ac9cf6f7052a601f3faa, artgraph_v1_phase_0_5_morris_louis).
has_genre(ag_72463, ag_6, agf_460af3f86fb80412b668).
source_fact(agf_460af3f86fb80412b668, has_genre, ag_72463, ag_6, 'https://www.gennarovessio.com/artgraph-schema#hasGenre').
fact_snapshot(agf_460af3f86fb80412b668, artgraph_v1_phase_0_5_morris_louis).
has_period(ag_72463, ag_133221, agf_ec4c54cd4fc6b8b6baaf).
source_fact(agf_ec4c54cd4fc6b8b6baaf, has_period, ag_72463, ag_133221, 'https://www.gennarovessio.com/artgraph-schema#hasPeriod').
fact_snapshot(agf_ec4c54cd4fc6b8b6baaf, artgraph_v1_phase_0_5_morris_louis).
has_style(ag_72463, ag_41, agf_48bcc01ef5c3d65e1cc6).
source_fact(agf_48bcc01ef5c3d65e1cc6, has_style, ag_72463, ag_41, 'https://www.gennarovessio.com/artgraph-schema#hasStyle').
fact_snapshot(agf_48bcc01ef5c3d65e1cc6, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72463, ag_2552, agf_28695cd3c80e17b46709).
source_fact(agf_28695cd3c80e17b46709, made_of, ag_72463, ag_2552, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_28695cd3c80e17b46709, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72463, ag_2602, agf_57361f2f336b4eb603f7).
source_fact(agf_57361f2f336b4eb603f7, made_of, ag_72463, ag_2602, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_57361f2f336b4eb603f7, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72463, 'morris-louis_where-1960.jpg', agf_ad0bc563c2f158856a3a).
source_fact(agf_ad0bc563c2f158856a3a, rdf_label, ag_72463, 'morris-louis_where-1960.jpg', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_ad0bc563c2f158856a3a, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72463, 'Where', agf_ec3979ea039607ff642d).
source_fact(agf_ec3979ea039607ff642d, rdf_label, ag_72463, 'Where', 'https://www.gennarovessio.com/artgraph-schema#title').
fact_snapshot(agf_ec3979ea039607ff642d, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_72464, artwork, agf_2f6a47a86d5547147922).
source_fact(agf_2f6a47a86d5547147922, rdf_type, ag_72464, artwork, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_2f6a47a86d5547147922, artgraph_v1_phase_0_5_morris_louis).
created_by(ag_72464, ag_1210, agf_81055b789e6adc16409b).
source_fact(agf_81055b789e6adc16409b, created_by, ag_72464, ag_1210, 'https://www.gennarovessio.com/artgraph-schema#createdBy').
fact_snapshot(agf_81055b789e6adc16409b, artgraph_v1_phase_0_5_morris_louis).
has_genre(ag_72464, ag_6, agf_a5b98366b304e8ea31f3).
source_fact(agf_a5b98366b304e8ea31f3, has_genre, ag_72464, ag_6, 'https://www.gennarovessio.com/artgraph-schema#hasGenre').
fact_snapshot(agf_a5b98366b304e8ea31f3, artgraph_v1_phase_0_5_morris_louis).
has_period(ag_72464, ag_133221, agf_85bf465e5dd4d9799802).
source_fact(agf_85bf465e5dd4d9799802, has_period, ag_72464, ag_133221, 'https://www.gennarovessio.com/artgraph-schema#hasPeriod').
fact_snapshot(agf_85bf465e5dd4d9799802, artgraph_v1_phase_0_5_morris_louis).
has_style(ag_72464, ag_41, agf_be633e3f92e271533855).
source_fact(agf_be633e3f92e271533855, has_style, ag_72464, ag_41, 'https://www.gennarovessio.com/artgraph-schema#hasStyle').
fact_snapshot(agf_be633e3f92e271533855, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72464, ag_2552, agf_ec0759e597b4ccf3d7bc).
source_fact(agf_ec0759e597b4ccf3d7bc, made_of, ag_72464, ag_2552, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_ec0759e597b4ccf3d7bc, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72464, ag_2630, agf_9b5b634da916e2a9f71f).
source_fact(agf_9b5b634da916e2a9f71f, made_of, ag_72464, ag_2630, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_9b5b634da916e2a9f71f, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72464, 'morris-louis_alpha-pi-1960.jpg', agf_9b74fe7383c893a23c4a).
source_fact(agf_9b74fe7383c893a23c4a, rdf_label, ag_72464, 'morris-louis_alpha-pi-1960.jpg', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_9b74fe7383c893a23c4a, artgraph_v1_phase_0_5_morris_louis).
part_of_series(ag_72464, ag_132972, agf_4b444ed275608a320cb5).
source_fact(agf_4b444ed275608a320cb5, part_of_series, ag_72464, ag_132972, 'https://www.gennarovessio.com/artgraph-schema#partOf').
fact_snapshot(agf_4b444ed275608a320cb5, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72464, 'Alpha-Pi', agf_e34636284e44993a2dc7).
source_fact(agf_e34636284e44993a2dc7, rdf_label, ag_72464, 'Alpha-Pi', 'https://www.gennarovessio.com/artgraph-schema#title').
fact_snapshot(agf_e34636284e44993a2dc7, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_72465, artwork, agf_c873efbf06438393a679).
source_fact(agf_c873efbf06438393a679, rdf_type, ag_72465, artwork, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_c873efbf06438393a679, artgraph_v1_phase_0_5_morris_louis).
created_by(ag_72465, ag_1210, agf_95e6c4ff6c4296d46d91).
source_fact(agf_95e6c4ff6c4296d46d91, created_by, ag_72465, ag_1210, 'https://www.gennarovessio.com/artgraph-schema#createdBy').
fact_snapshot(agf_95e6c4ff6c4296d46d91, artgraph_v1_phase_0_5_morris_louis).
has_genre(ag_72465, ag_6, agf_9f9a16805366c8845d1e).
source_fact(agf_9f9a16805366c8845d1e, has_genre, ag_72465, ag_6, 'https://www.gennarovessio.com/artgraph-schema#hasGenre').
fact_snapshot(agf_9f9a16805366c8845d1e, artgraph_v1_phase_0_5_morris_louis).
has_period(ag_72465, ag_133221, agf_51fa8cc541b754d39546).
source_fact(agf_51fa8cc541b754d39546, has_period, ag_72465, ag_133221, 'https://www.gennarovessio.com/artgraph-schema#hasPeriod').
fact_snapshot(agf_51fa8cc541b754d39546, artgraph_v1_phase_0_5_morris_louis).
has_style(ag_72465, ag_41, agf_15a26529320d354b3022).
source_fact(agf_15a26529320d354b3022, has_style, ag_72465, ag_41, 'https://www.gennarovessio.com/artgraph-schema#hasStyle').
fact_snapshot(agf_15a26529320d354b3022, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72465, ag_2552, agf_bfca9251826dee73d9cb).
source_fact(agf_bfca9251826dee73d9cb, made_of, ag_72465, ag_2552, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_bfca9251826dee73d9cb, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72465, 'morris-louis_beta-lambda-1961.jpg', agf_16a3720c3715d15ec1a7).
source_fact(agf_16a3720c3715d15ec1a7, rdf_label, ag_72465, 'morris-louis_beta-lambda-1961.jpg', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_16a3720c3715d15ec1a7, artgraph_v1_phase_0_5_morris_louis).
part_of_series(ag_72465, ag_132972, agf_c40a8d5af152111b7786).
source_fact(agf_c40a8d5af152111b7786, part_of_series, ag_72465, ag_132972, 'https://www.gennarovessio.com/artgraph-schema#partOf').
fact_snapshot(agf_c40a8d5af152111b7786, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72465, 'Beta Lambda', agf_a46eca7c92eb54b89df9).
source_fact(agf_a46eca7c92eb54b89df9, rdf_label, ag_72465, 'Beta Lambda', 'https://www.gennarovessio.com/artgraph-schema#title').
fact_snapshot(agf_a46eca7c92eb54b89df9, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_72466, artwork, agf_10dd667e95c0d54f1cfb).
source_fact(agf_10dd667e95c0d54f1cfb, rdf_type, ag_72466, artwork, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_10dd667e95c0d54f1cfb, artgraph_v1_phase_0_5_morris_louis).
created_by(ag_72466, ag_1210, agf_2f4cdbac43ced9a0620c).
source_fact(agf_2f4cdbac43ced9a0620c, created_by, ag_72466, ag_1210, 'https://www.gennarovessio.com/artgraph-schema#createdBy').
fact_snapshot(agf_2f4cdbac43ced9a0620c, artgraph_v1_phase_0_5_morris_louis).
has_genre(ag_72466, ag_6, agf_1ddad2073b88fc2c6078).
source_fact(agf_1ddad2073b88fc2c6078, has_genre, ag_72466, ag_6, 'https://www.gennarovessio.com/artgraph-schema#hasGenre').
fact_snapshot(agf_1ddad2073b88fc2c6078, artgraph_v1_phase_0_5_morris_louis).
has_period(ag_72466, ag_133221, agf_9a9774e5caf14947b742).
source_fact(agf_9a9774e5caf14947b742, has_period, ag_72466, ag_133221, 'https://www.gennarovessio.com/artgraph-schema#hasPeriod').
fact_snapshot(agf_9a9774e5caf14947b742, artgraph_v1_phase_0_5_morris_louis).
has_style(ag_72466, ag_41, agf_ddfcd93f108c6c460da9).
source_fact(agf_ddfcd93f108c6c460da9, has_style, ag_72466, ag_41, 'https://www.gennarovessio.com/artgraph-schema#hasStyle').
fact_snapshot(agf_ddfcd93f108c6c460da9, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72466, ag_2552, agf_7bb729a73a995c273a51).
source_fact(agf_7bb729a73a995c273a51, made_of, ag_72466, ag_2552, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_7bb729a73a995c273a51, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72466, ag_2630, agf_0e4cf72e11a010a1de68).
source_fact(agf_0e4cf72e11a010a1de68, made_of, ag_72466, ag_2630, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_0e4cf72e11a010a1de68, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72466, 'morris-louis_partition-1962.jpg', agf_a5994db10f8aa8ab0167).
source_fact(agf_a5994db10f8aa8ab0167, rdf_label, ag_72466, 'morris-louis_partition-1962.jpg', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_a5994db10f8aa8ab0167, artgraph_v1_phase_0_5_morris_louis).
part_of_series(ag_72466, ag_132587, agf_56d6936789cafd621e74).
source_fact(agf_56d6936789cafd621e74, part_of_series, ag_72466, ag_132587, 'https://www.gennarovessio.com/artgraph-schema#partOf').
fact_snapshot(agf_56d6936789cafd621e74, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72466, 'Partition', agf_e2a4741f437f2524e6f9).
source_fact(agf_e2a4741f437f2524e6f9, rdf_label, ag_72466, 'Partition', 'https://www.gennarovessio.com/artgraph-schema#title').
fact_snapshot(agf_e2a4741f437f2524e6f9, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_72467, artwork, agf_902a7e3b4c2a3b56aa39).
source_fact(agf_902a7e3b4c2a3b56aa39, rdf_type, ag_72467, artwork, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_902a7e3b4c2a3b56aa39, artgraph_v1_phase_0_5_morris_louis).
created_by(ag_72467, ag_1210, agf_4b1bfba1ada635dcbd64).
source_fact(agf_4b1bfba1ada635dcbd64, created_by, ag_72467, ag_1210, 'https://www.gennarovessio.com/artgraph-schema#createdBy').
fact_snapshot(agf_4b1bfba1ada635dcbd64, artgraph_v1_phase_0_5_morris_louis).
has_genre(ag_72467, ag_6, agf_4dce7997d120a2b984e2).
source_fact(agf_4dce7997d120a2b984e2, has_genre, ag_72467, ag_6, 'https://www.gennarovessio.com/artgraph-schema#hasGenre').
fact_snapshot(agf_4dce7997d120a2b984e2, artgraph_v1_phase_0_5_morris_louis).
has_period(ag_72467, ag_133221, agf_bc1a454b5d172abb22bb).
source_fact(agf_bc1a454b5d172abb22bb, has_period, ag_72467, ag_133221, 'https://www.gennarovessio.com/artgraph-schema#hasPeriod').
fact_snapshot(agf_bc1a454b5d172abb22bb, artgraph_v1_phase_0_5_morris_louis).
has_style(ag_72467, ag_41, agf_c88514678af6877f06d8).
source_fact(agf_c88514678af6877f06d8, has_style, ag_72467, ag_41, 'https://www.gennarovessio.com/artgraph-schema#hasStyle').
fact_snapshot(agf_c88514678af6877f06d8, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72467, ag_2552, agf_70df3e5912b9865d0ea9).
source_fact(agf_70df3e5912b9865d0ea9, made_of, ag_72467, ag_2552, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_70df3e5912b9865d0ea9, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72467, ag_2630, agf_70b274bbec2219f0121b).
source_fact(agf_70b274bbec2219f0121b, made_of, ag_72467, ag_2630, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_70b274bbec2219f0121b, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72467, 'morris-louis_phi-1961.jpg', agf_ca954608e6b5469bbc0f).
source_fact(agf_ca954608e6b5469bbc0f, rdf_label, ag_72467, 'morris-louis_phi-1961.jpg', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_ca954608e6b5469bbc0f, artgraph_v1_phase_0_5_morris_louis).
part_of_series(ag_72467, ag_132972, agf_478ed38da9e7ee9c9ff7).
source_fact(agf_478ed38da9e7ee9c9ff7, part_of_series, ag_72467, ag_132972, 'https://www.gennarovessio.com/artgraph-schema#partOf').
fact_snapshot(agf_478ed38da9e7ee9c9ff7, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72467, 'Phi', agf_1c35812503ff6d0e1152).
source_fact(agf_1c35812503ff6d0e1152, rdf_label, ag_72467, 'Phi', 'https://www.gennarovessio.com/artgraph-schema#title').
fact_snapshot(agf_1c35812503ff6d0e1152, artgraph_v1_phase_0_5_morris_louis).
rdf_type(ag_72468, artwork, agf_b7ee7696dba30ecce933).
source_fact(agf_b7ee7696dba30ecce933, rdf_type, ag_72468, artwork, 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type').
fact_snapshot(agf_b7ee7696dba30ecce933, artgraph_v1_phase_0_5_morris_louis).
created_by(ag_72468, ag_1210, agf_49c46f30ca2dae728696).
source_fact(agf_49c46f30ca2dae728696, created_by, ag_72468, ag_1210, 'https://www.gennarovessio.com/artgraph-schema#createdBy').
fact_snapshot(agf_49c46f30ca2dae728696, artgraph_v1_phase_0_5_morris_louis).
has_genre(ag_72468, ag_6, agf_f6f8c7b24ec406b364f8).
source_fact(agf_f6f8c7b24ec406b364f8, has_genre, ag_72468, ag_6, 'https://www.gennarovessio.com/artgraph-schema#hasGenre').
fact_snapshot(agf_f6f8c7b24ec406b364f8, artgraph_v1_phase_0_5_morris_louis).
has_period(ag_72468, ag_133221, agf_4db0889be5a9c9bd1b14).
source_fact(agf_4db0889be5a9c9bd1b14, has_period, ag_72468, ag_133221, 'https://www.gennarovessio.com/artgraph-schema#hasPeriod').
fact_snapshot(agf_4db0889be5a9c9bd1b14, artgraph_v1_phase_0_5_morris_louis).
has_style(ag_72468, ag_41, agf_6f47abe72de336fbd81e).
source_fact(agf_6f47abe72de336fbd81e, has_style, ag_72468, ag_41, 'https://www.gennarovessio.com/artgraph-schema#hasStyle').
fact_snapshot(agf_6f47abe72de336fbd81e, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72468, ag_2552, agf_940d716c6ebe934a6e2f).
source_fact(agf_940d716c6ebe934a6e2f, made_of, ag_72468, ag_2552, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_940d716c6ebe934a6e2f, artgraph_v1_phase_0_5_morris_louis).
made_of(ag_72468, ag_2630, agf_c00a37fd26e421b6041b).
source_fact(agf_c00a37fd26e421b6041b, made_of, ag_72468, ag_2630, 'https://www.gennarovessio.com/artgraph-schema#madeOf').
fact_snapshot(agf_c00a37fd26e421b6041b, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72468, 'morris-louis_vav-1960.jpg', agf_bf1f8f7339d9b6d27010).
source_fact(agf_bf1f8f7339d9b6d27010, rdf_label, ag_72468, 'morris-louis_vav-1960.jpg', 'https://www.gennarovessio.com/artgraph-schema#name').
fact_snapshot(agf_bf1f8f7339d9b6d27010, artgraph_v1_phase_0_5_morris_louis).
part_of_series(ag_72468, ag_132804, agf_f64a093fe5fabb9edb1b).
source_fact(agf_f64a093fe5fabb9edb1b, part_of_series, ag_72468, ag_132804, 'https://www.gennarovessio.com/artgraph-schema#partOf').
fact_snapshot(agf_f64a093fe5fabb9edb1b, artgraph_v1_phase_0_5_morris_louis).
rdf_label(ag_72468, 'VAV', agf_6bcbbdefd183a3a4edf8).
source_fact(agf_6bcbbdefd183a3a4edf8, rdf_label, ag_72468, 'VAV', 'https://www.gennarovessio.com/artgraph-schema#title').
fact_snapshot(agf_6bcbbdefd183a3a4edf8, artgraph_v1_phase_0_5_morris_louis).
