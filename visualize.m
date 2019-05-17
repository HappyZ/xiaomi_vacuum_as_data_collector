rawdata = readtable('./example/20190505_170223_sig/1c36bb06203c.csv');
data = table2array(rawdata(:, [1,2,4,5,9]));
unique_types = unique(data(:,5));

figure(1); clf;
for j = 1:size(unique_types, 1)
    logistics = data(:,5) == unique_types(j);
    tmpdata = data(logistics, :);
    unique_xys = unique(tmpdata(:, 1:2), 'row');
    tmpdata_avg = [];
    for i = size(unique_xys, 1):-1:1
        xy_logistics = unique_xys(i, 1:2) == tmpdata(:, 1:2);
        xy_logistics = xy_logistics(:,1) & xy_logistics(:,2);
        tmpdata_avg(i, :) = [unique_xys(i, 1:2), mean(tmpdata(xy_logistics, 3:end), 1)];
    end
    ax1 = subplot(size(unique_types, 1), 3, 3 * j - 2);
    scatter3(tmpdata_avg(:,1), tmpdata_avg(:,2), tmpdata_avg(:,3), 100, tmpdata_avg(:,4), '.');
    caxis([-85, -20]); view([0, 90]);
    xlabel('loc x (m)'); ylabel('loc y (m)'); zlabel('time (s)'); 
    title(['packet type: ', num2str(unique_types(j))])
    
    ax2 = subplot(size(unique_types, 1), 3, 3 * j - 1);
    scatter3(tmpdata_avg(:,1), tmpdata_avg(:,2), tmpdata_avg(:,4), 100, tmpdata_avg(:,4), '.');
    center_x = mean(unique_xys(:,1));
    center_y = mean(unique_xys(:,2));
    xlim([-3.2, 3.2] + center_x); ylim([-3.2, 3.2] + center_y);
    caxis([-85, -20]);
    xlabel('loc x (m)'); ylabel('loc y (m)'); zlabel('RSS (dB)'); 
    title(['packet type: ', num2str(unique_types(j))])
    
    mymap = ones(64, 64) * -85;
    for ii = 1:64
        x_upper = center_x + 0.1 * (ii - 32);
        x_lower = center_x + 0.1 * (ii - 1 - 32);
        x_logistics = tmpdata(:, 1) >= x_lower & tmpdata(:, 1) <= x_upper;
        if sum(x_logistics) == 0
            continue;
        end
        for jj = 1:64
            y_upper = center_y + 0.1 * (jj - 32);
            y_lower = center_y + 0.1 * (jj - 1 - 32);
            y_logistics = tmpdata(:, 2) >= y_lower & tmpdata(:, 2) <= y_upper;
            logistics = x_logistics & y_logistics;
            if sum(logistics) > 0
                mymap(jj, ii) = median(tmpdata(logistics, 4));
            end
        end
    end
    ax3 = subplot(size(unique_types, 1), 3, 3 * j);
    surf(mymap, 'EdgeColor', 'None'); view([0, 90]);
    xlim([1, 64]); ylim([1, 64]); 
    
    colorbar;
end